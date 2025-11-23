#!/usr/bin/env python3
"""
Global Regime v3 의존성 설치 스크립트
"""
import subprocess
import sys

def install_dependencies():
    """Global Regime v3에 필요한 패키지 설치 (yfinance 제거)"""
    packages = [
        'pandas>=1.5.0',
        'numpy>=1.20.0',
        'psycopg[binary]>=3.0.0'
    ]
    
    for package in packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            return False
    
    print("\n🎉 All dependencies installed successfully!")
    return True

if __name__ == "__main__":
    install_dependencies()