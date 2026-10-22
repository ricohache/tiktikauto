import sys
print('Python:', sys.version)
print('Path:', sys.executable)
try:
    import torch
    print('PyTorch:', torch.__version__)
    print('CUDA disponible:', torch.cuda.is_available())
    if torch.cuda.is_available():
        print('GPU:', torch.cuda.get_device_name(0))
        print('VRAM:', torch.cuda.get_device_properties(0).total_memory / 1024**3, 'Go')
except Exception as e:
    print('Erreur:', e)
