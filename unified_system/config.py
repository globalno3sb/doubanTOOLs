# -*- coding: utf-8 -*-
"""
统一系统配置模块
"""
import os
import json

def get_user_input():
    """获取用户输入的所有配置"""
    print("=" * 60)
    print("豆瓣到 Trakt 统一系统配置")
    print("=" * 60)
    
    # Trakt 应用凭据
    print("\n1. Trakt 应用凭据:")
    print("-" * 30)
    client_id = input("Trakt Client ID: ").strip()
    client_secret = input("Trakt Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("错误: Client ID 和 Client Secret 不能为空")
        return None
    
    # 豆瓣配置
    print("\n2. 豆瓣配置:")
    print("-" * 30)
    douban_user_id = input("豆瓣用户ID: ").strip()
    start_date = input("起始日期 (YYYYMMDD, 默认全部): ").strip() or "20050502"
    
    if not douban_user_id:
        print("错误: 豆瓣用户ID不能为空")
        return None
    
    # 输出配置
    print("\n3. 输出配置:")
    print("-" * 30)
    csv_output = input("CSV输出文件 [默认: movie.csv]: ").strip() or "movie.csv"
    token_output = input("令牌输出文件 [默认: token.json]: ").strip() or "token.json"
    
    # 运行模式
    print("\n4. 运行模式:")
    print("-" * 30)
    dry_run = input("启用干运行模式? (y/N): ").strip().lower() == 'y'
    
    return {
        'trakt': {
            'client_id': client_id,
            'client_secret': client_secret,
            'token_file': token_output
        },
        'douban': {
            'user_id': douban_user_id,
            'start_date': start_date,
            'deep_refine': True,
            'csv_output': csv_output
        },
        'system': {
            'dry_run': dry_run
        }
    }

def load_token(token_file):
    """加载令牌文件"""
    if not os.path.exists(token_file):
        return None
    
    try:
        with open(token_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def save_token(token_data, token_file):
    """保存令牌文件"""
    try:
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存令牌失败: {e}")
        return False