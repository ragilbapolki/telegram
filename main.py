from datetime import datetime
from config import CURRENT_DATE
from report_app import ReportApp
import logging
import sys

if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('report_app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    app = ReportApp()
    success = app.run_report_with_national_and_regional()
    if success:
        logging.info("✓ Report application completed successfully!")
    else:
        logging.error("X Report application failed!")
    return success

if __name__ == "__main__":
    main()