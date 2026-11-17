#!/usr/bin/env python3
"""Django 命令行入口。项目 4 的被测商城与可视化看板都由它启动。"""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
