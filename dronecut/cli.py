import argparse
import logging
import sys
from .core.pipeline import DroneCutPipeline

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="DroneCut: Intelligent drone video editor.")
    parser.add_argument("--inputs", nargs="+", required=True, help="Input video files.")
    parser.add_argument("--out-dir", default="dronecut_output", help="Output directory for clips and final video.")
    parser.add_argument("--prompts", nargs="+", help="Positive semantic prompts (e.g. 'mountain', 'sunset').")
    parser.add_argument("--neg-prompts", nargs="+", help="Negative semantic prompts (e.g. 'blur', 'crowd').")
    parser.add_argument("--max-scenes", type=int, default=40, help="Max scenes in the final video.")
    parser.add_argument("--speed", type=float, default=1.5, help="Speedup factor (default 1.5).")
    parser.add_argument("--max-duration", type=int, help="Target max duration in seconds for final video.")
    parser.add_argument("--music", help="Path to background music file for beat sync.")
    parser.add_argument("--threshold", type=float, default=20.0, help="Scene detection threshold (default 20.0).")
    parser.add_argument("--min-duration", type=float, default=1.5, help="Minimum scene duration (default 1.5).")
    parser.add_argument("--no-export", action="store_true", help="Skip final montage, only extract scenes.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    try:
        pipeline = DroneCutPipeline(
            prompts=args.prompts, 
            negative_prompts=args.neg_prompts,
            max_scenes=args.max_scenes,
            speed=args.speed,
            max_duration=args.max_duration,
            min_scene_duration=args.min_duration,
            threshold=args.threshold,
            music_path=args.music
        )
        
        logger.info("Starting DroneCut Cinematic Pipeline...")
        scenes = pipeline.analyze(
            args.inputs, 
            args.out_dir, 
            skip_export=args.no_export
        )
        
        logger.info(f"Analysis complete. Found {len(scenes)} potential scenes.")
        
        logger.info(f"Processing complete. Final video saved in {args.out_dir}")
        
    except Exception as e:
        logging.error(f"Critical error: {e}")
        import traceback
        logging.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
