# -*- coding: utf-8 -*-
"""
配置模块 - 处理用户输入和配置
"""

def get_trakt_app_credentials():
    """
    引导用户获取 Trakt 应用凭据的步骤说明
    """
    print("=" * 60)
    print("获取 Trakt 应用凭据步骤:")
    print("=" * 60)
    print("1. 访问 https://trakt.tv/oauth/applications")
    print("2. 点击 'NEW APPLICATION' 创建新应用")
    print("3. 填写应用信息:")
    print("   - Name: 你的应用名称")
    print("   - Description: 应用描述")
    print("   - Redirect uri: https://localhost (或其他有效URL)")
    print("4. 创建后复制 'Client ID' 和 'Client Secret'")
    print("=" * 60)
    
    client_id = input("请输入你的 Trakt Client ID: ").strip()
    client_secret = input("请输入你的 Trakt Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("错误: Client ID 和 Client Secret 不能为空")
        return None, None
    
    return client_id, client_secret

def get_output_path():
    """
    获取输出文件路径
    """
    default_path = "token.json"
    path = input(f"请输入输出文件路径 [默认: {default_path}]: ").strip()
    return path or default_path