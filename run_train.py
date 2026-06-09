"""Launch training — output goes to stdout, .bat redirects to file"""
import sys, os, datetime
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

print(f"[{datetime.datetime.now()}] Starting 30-epoch training...", flush=True)
print(f"Python: {sys.executable}", flush=True)

sys.argv = ['train', '--data_dir', './dataset', '--epochs', '30', '--batch_size', '32']
from src.train import main
main()
print(f"[{datetime.datetime.now()}] Done.", flush=True)
