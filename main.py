import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import TranslatorApp


def main():
    app = TranslatorApp()
    app.run()


if __name__ == "__main__":
    main()
