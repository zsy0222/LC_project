@echo off
chcp 65001 >nul
cd /d C:\Users\chenm\Desktop\program\LC_project
C:\Users\chenm\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe -u -c "import sys;sys.path.insert(0,'.');sys.argv=['train','--data_dir','./dataset','--epochs','30','--batch_size','32'];from src.train import main;main()" > train_output.txt 2>&1
