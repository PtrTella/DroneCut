import argparse
import logging
import sys
from .core.pipeline import DroneCutPipeline

def main():
    parser = argparse.ArgumentParser(description="DroneCut: Intelligent drone video editor.")
    parser.add_argument("--inputs", nargs="+", required=True, help="Input video files.")
    parser.add_argument("--out-dir", default="dronecut_output", help="Output directory for clips and final video.")
    parser.add_argument("--prompts", nargs="+", help="Semantic prompts for CLIP scoring.")
    parser.add_argument("--max-scenes", type=int, default=40, help="Max scenes in the final video.")
    parser.add_argument("--speed", type=float, default=1.5, help="Speedup factor (default 1.5).")
    parser.add_argument("--max-duration", type=int, help="Target max duration in seconds for final video.")
    parser.add_argument("--music", help="Path to background music file for beat sync.")
    parser.add_argument("--threshold", type=float, default=20.0, help="Scene detection threshold (default 20.0, lower = more cuts).")
    parser.add_argument("--min-duration", type=float, default=1.5, help="Minimum scene duration in seconds (default 1.5).")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    try:
        pipeline = DroneCutPipeline(
            prompts=args.prompts, 
            max_scenes=args.max_scenes,
            speed=args.speed,
            max_duration=args.max_duration,
            min_scene_duration=args.min_duration,
            music_path=args.music
        )
        # We need to pass the threshold to detect_scenes somehow. 
        # For now let's modify pipeline.run to accept it or just set it in __init__.
        pipeline.threshold = args.threshold
        pipeline.run(args.inputs, args.out_dir)
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
