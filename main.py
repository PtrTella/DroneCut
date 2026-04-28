import sys
import logging
import argparse
from src.pipeline import DroneCutPipeline

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("DroneAutoCutter")

def main():
    parser = argparse.ArgumentParser(description="DroneCut V3: AI-Powered Automated Drone Video Editor")
    parser.add_argument("video_path", help="Path to the input video file")
    parser.add_argument("--theme", help="Optional theme prompt for creative selection", default=None)
    
    args = parser.parse_args()

    pipeline = DroneCutPipeline()
    try:
        results = pipeline.run(args.video_path, args.theme)
        if results:
            logger.info(f"✅ Pipeline finished successfully. {len(results)} clips selected.")
        else:
            logger.warning("⚠️ No clips were selected.")
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
