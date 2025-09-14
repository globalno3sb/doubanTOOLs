# -*- coding: utf-8 -*-
"""
统一系统协调器 - 协调所有子系统工作流程
"""
import sys
import os
import subprocess
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_get_pin_trakt(config):
    """运行获取令牌流程"""
    print("\n" + "=" * 60)
    print("步骤 1/3: 获取 Trakt 访问令牌")
    print("=" * 60)
    
    # 检查是否已有有效令牌
    from .config import load_token
    token_data = load_token(config['trakt']['token_file'])
    
    if token_data:
        print("发现现有令牌文件，跳过获取令牌步骤")
        return token_data
    
    # 需要获取新令牌
    print("需要获取新的 Trakt 访问令牌")
    
    # 导入 get_pin_trakt 模块功能
    try:
        from get_pin_trakt.auth import get_device_code, poll_for_token
        from get_pin_trakt.config import get_trakt_app_credentials
    except ImportError:
        print("错误: 无法导入 get_pin_trakt 模块")
        return None
    
    # 获取设备代码
    device_data = get_device_code(config['trakt']['client_id'])
    if not device_data:
        print("获取设备代码失败")
        return None
    
    device_code = device_data["device_code"]
    user_code = device_data["user_code"]
    verification_url = device_data["verification_url"]
    expires_in = device_data["expires_in"]
    interval = device_data["interval"]
    
    print(f"请访问: {verification_url}")
    print(f"输入 PIN 码: {user_code}")
    print(f"有效期: {expires_in // 60} 分钟")
    
    # 轮询获取令牌
    token_data = poll_for_token(
        device_code, interval, expires_in, 
        config['trakt']['client_id'], config['trakt']['client_secret']
    )
    
    if token_data:
        from .config import save_token
        if save_token(token_data, config['trakt']['token_file']):
            print(f"令牌已保存到: {config['trakt']['token_file']}")
        return token_data
    else:
        print("获取令牌失败")
        return None

def run_douban_to_csv(config):
    """运行豆瓣到 CSV 转换流程"""
    print("\n" + "=" * 60)
    print("步骤 2/3: 从豆瓣抓取数据并生成 CSV")
    print("=" * 60)
    
    # 构建命令行参数
    cmd = [
        sys.executable, "douban_to_csv/douban_to_csv.py",
        config['douban']['user_id'],
        config['douban']['start_date'],
        "--deep-refine",
        "--trakt-client-id", config['trakt']['client_id'],
        "--out", config['douban']['csv_output']
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        if result.returncode == 0:
            print("豆瓣数据抓取成功")
            print(result.stdout)
            return True
        else:
            print("豆瓣数据抓取失败")
            print("STDERR:", result.stderr)
            print("STDOUT:", result.stdout)
            return False
            
    except Exception as e:
        print(f"执行豆瓣抓取时发生错误: {e}")
        return False

def run_csv_to_trakt(config, token_data):
    """运行 CSV 到 Trakt 同步流程"""
    print("\n" + "=" * 60)
    print("步骤 3/3: 同步数据到 Trakt")
    print("=" * 60)
    
    if not token_data or 'access_token' not in token_data:
        print("错误: 没有有效的访问令牌")
        return False
    
    # 构建命令行参数
    cmd = [
        sys.executable, "csv_to_trakt/csv_to_trakt.py",
        "--csv", config['douban']['csv_output'],
        "--type", "watched",
        "--trakt-client-id", config['trakt']['client_id'],
        "--trakt-token", token_data['access_token']
    ]
    
    if config['system']['dry_run']:
        cmd.append("--dry-run")
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        if result.returncode == 0:
            print("Trakt 同步成功")
            print(result.stdout)
            return True
        else:
            print("Trakt 同步失败")
            print("STDERR:", result.stderr)
            print("STDOUT:", result.stdout)
            return False
            
    except Exception as e:
        print(f"执行 Trakt 同步时发生错误: {e}")
        return False

def run_unified_workflow(config):
    """运行统一工作流程"""
    print("开始执行豆瓣到 Trakt 统一工作流程")
    print("Dry-run 模式:", "启用" if config['system']['dry_run'] else "禁用")
    
    # 步骤1: 获取令牌
    token_data = run_get_pin_trakt(config)
    if not token_data:
        print("令牌获取失败，终止流程")
        return False
    
    # 步骤2: 豆瓣数据抓取
    if not run_douban_to_csv(config):
        print("豆瓣数据抓取失败，终止流程")
        return False
    
    # 步骤3: Trakt 同步
    if not run_csv_to_trakt(config, token_data):
        print("Trakt 同步失败")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有步骤完成!")
    print("=" * 60)
    
    if config['system']['dry_run']:
        print("注意: 运行在干运行模式，未实际修改 Trakt 数据")
    else:
        print("数据已成功同步到 Trakt")
    
    return True