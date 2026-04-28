import os
import subprocess
import logging
import json
import cv2
import numpy as np
from PIL import Image
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from .config import OUTPUT_DIR, DBSCAN_EPS, DBSCAN_MIN_SAMPLES, AMBIGUITY_THRESHOLD, AESTHETIC_THRESHOLD, TOP_K_PER_CLUSTER, RELEVANCE_THRESHOLD

logger = logging.getLogger(__name__)

class Director:
    def __init__(self, output_dir=OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def cluster_and_filter_v3(self, scenes):
        if not scenes: return [], []
        
        embeddings = np.array([s["clip_embedding"] for s in scenes])
        dbscan = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES, metric='cosine')
        labels = dbscan.fit_predict(embeddings)
        
        survivors = []
        discarded = []
        cluster_centroids = {}
        
        for label in set(labels):
            if label == -1: continue
            mask = (labels == label)
            cluster_centroids[label] = np.mean(embeddings[mask], axis=0)

        for i, scene in enumerate(scenes):
            label = labels[i]
            scene["cluster_id"] = int(label)
            
            if label == -1:
                scene["discard_reason"] = "Semantic_Noise"
                discarded.append(scene)
                continue
            
            centroid = cluster_centroids[label]
            distance = np.linalg.norm(scene["clip_embedding"] - centroid)
            scene["centroid_distance"] = float(distance)
            
            if distance > AMBIGUITY_THRESHOLD:
                scene["discard_reason"] = f"Ambiguity_dist_{distance:.2f}"
                discarded.append(scene)
                continue
                
            survivors.append(scene)
            
        return survivors, discarded

    def visualize_clusters(self, scenes, output_path):
        """
        Genera una mappa 2D del clustering usando PCA.
        """
        try:
            import matplotlib.pyplot as plt
            if not scenes: return
            
            embeddings = np.array([s["clip_embedding"] for s in scenes])
            labels = np.array([s["cluster_id"] for s in scenes])
            
            if len(embeddings) < 2: return
            
            pca = PCA(n_components=2)
            reduced = pca.fit_transform(embeddings)
            
            plt.figure(figsize=(10, 8))
            scatter = plt.scatter(reduced[:, 0], reduced[:, 1], c=labels, cmap='gist_ncar', alpha=0.6)
            plt.colorbar(scatter, label='Cluster ID')
            plt.title(f"DroneCut Clustering Map (DBSCAN eps={DBSCAN_EPS})")
            plt.xlabel("PCA 1")
            plt.ylabel("PCA 2")
            plt.grid(True, alpha=0.3)
            plt.savefig(output_path)
            plt.close()
            logger.info(f"Clustering map saved to {output_path}")
        except Exception as e:
            logger.warning(f"Could not generate clustering map: {e}")

    def run_creative_selection(self, scored_scenes, evaluator, theme_prompt=None):
        clusters = {}
        for s in scored_scenes:
            cid = s["cluster_id"]
            if cid not in clusters: clusters[cid] = []
            clusters[cid].append(s)
            
        final_selection = []
        vlm_discarded = []
        
        logger.info(f"VLM Director: Auditing {len(scored_scenes)} scenes...")
        
        for cid, cluster in clusters.items():
            cluster.sort(key=lambda x: x.get("aesthetic_score", 0), reverse=True)
            
            valid_in_cluster = []
            for scene in cluster:
                if "_temp_frame" not in scene: continue
                
                img = Image.fromarray(cv2.cvtColor(scene["_temp_frame"], cv2.COLOR_BGR2RGB))
                
                # 1. Quality Audit
                if not evaluator.audit_quality(img):
                    scene["discard_reason"] = "VLM_Bad_Framing"
                    vlm_discarded.append(scene)
                    continue
                
                # 2. Relevance Score
                if theme_prompt:
                    rel_score = evaluator.calculate_relevance(img, theme_prompt)
                    scene["relevance_score"] = rel_score
                    if rel_score < RELEVANCE_THRESHOLD:
                        scene["discard_reason"] = f"VLM_Low_Relevance_{rel_score}"
                        vlm_discarded.append(scene)
                        continue
                
                # 3. Final Captioning
                scene["caption"] = evaluator.generate_caption(img).strip().lower()
                valid_in_cluster.append(scene)
                
                if len(valid_in_cluster) >= TOP_K_PER_CLUSTER:
                    # Mark the rest as discarded by "Podium Rule" if we care to see them
                    break
            
            final_selection.extend(valid_in_cluster)
            
        return final_selection, vlm_discarded

    def save_debug_report(self, all_discarded):
        report_path = os.path.join(self.output_dir, "debug_report.json")
        summary = {
            "total_discarded": len(all_discarded),
            "reasons": {}
        }
        for s in all_discarded:
            reason = s.get("discard_reason", "unknown")
            summary["reasons"][reason] = summary["reasons"].get(reason, 0) + 1
            
        report = {
            "summary": summary,
            "details": [
                {
                    "id": s.get("id"),
                    "start": s.get("start_sec"),
                    "end": s.get("end_sec"),
                    "reason": s.get("discard_reason"),
                    "aesthetic_score": s.get("aesthetic_score"),
                    "relevance_score": s.get("relevance_score"),
                    "cluster_id": s.get("cluster_id")
                } for s in all_discarded
            ]
        }
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Debug report saved to {report_path}")

    def export_debug_frames(self, video_path, scenes, debug_dir):
        os.makedirs(debug_dir, exist_ok=True)
        cap = cv2.VideoCapture(video_path)
        for scene in scenes:
            mid_sec = (scene["start_sec"] + scene["end_sec"]) / 2
            cap.set(cv2.CAP_PROP_POS_MSEC, mid_sec * 1000)
            ret, frame = cap.read()
            if ret:
                reason = scene.get("discard_reason", "unknown")
                filename = f"scene_{scene['id']}_{reason}.jpg"
                path = os.path.join(debug_dir, filename)
                cv2.imwrite(path, frame)
        cap.release()

    def export_timeline(self, video_path, scenes):
        target_dir = os.path.join(self.output_dir, "timeline")
        os.makedirs(target_dir, exist_ok=True)
        for i, scene in enumerate(scenes):
            start = scene.get("trimmed_start", scene["start_sec"])
            end = scene.get("trimmed_end", scene["end_sec"])
            duration = end - start
            filename = f"shot_{i:03d}_cluster_{scene['cluster_id']}_id_{scene['id']}.mp4"
            output_path = os.path.join(target_dir, filename)
            cmd = [
                "ffmpeg", "-y", "-ss", str(start), "-t", str(duration),
                "-i", video_path, "-c", "copy", "-avoid_negative_ts", "make_non_negative",
                output_path
            ]
            subprocess.run(cmd, capture_output=True)

    def save_manifest(self, selected_scenes):
        def clean(c):
            res = c.copy()
            res.pop("clip_embedding", None)
            res.pop("_temp_frame", None)
            return res
        manifest = {
            "timeline": [clean(c) for c in selected_scenes],
            "metadata": {
                "total_shots": len(selected_scenes),
                "clusters": len(set(s["cluster_id"] for s in selected_scenes))
            }
        }
        with open(os.path.join(self.output_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
