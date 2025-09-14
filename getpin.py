#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trakt PIN 码获取工具 - 简化版
此版本保留原有功能，提供更简单的使用方式
"""
import requests
import time
import json

def show_instructions():
    """显示使用说明"""
    print("=" * 70)
    print("Trakt PIN 码获取工具 - 使用说明")
    print("=" * 70)
    print("1. 首先需要获取 Trakt 应用凭据:")
    print("   - 访问 https://trakt.tv/oauth/applications")
    print("   - 创建新应用并获取 Client ID 和 Client Secret")
    print("2. 运行此程序时会要求输入这些凭据")
    print("3. 程序会生成一个 PIN 码，需要在浏览器中授权")
    print("4. 授权成功后会自动获取访问令牌")
    print("=" * 70)
    print()

def get_credentials():
    """获取用户输入的凭据"""
    print("请输入你的 Trakt 应用凭据:")
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("错误: Client ID 和 Client Secret 不能为空")
        return None, None
    
    return client_id, client_secret

def get_device_code(client_id):
    """获取设备代码"""
    url = "https://api.trakt.tv/oauth/device/code"
    payload = {"client_id": client_id}
    
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"获取设备代码失败: {e}")
        return None

def poll_for_token(device_code, interval, expires_in, client_id, client_secret):
    """轮询获取访问令牌"""
    url = "https://api.trakt.tv/oauth/device/token"
    payload = {
        "code": device_code,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    start_time = time.time()
    
    print("\n请按照以下步骤操作:")
    print("1. 在浏览器中打开上述验证网址")
    print("2. 输入显示的 PIN 码")
    print("3. 授权应用程序")
    print("4. 等待系统自动获取访问令牌...")
    print("-" * 50)

    while time.time() - start_time < expires_in:
        try:
            r = requests.post(url, json=payload, timeout=30)
            
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 400:
                # 授权还没确认，继续等待
                pass
            elif r.status_code == 418:
                print("授权尚未确认，请检查是否已完成浏览器中的授权步骤")
            elif r.status_code == 429:
                print("请求过于频繁，等待稍后重试...")
                time.sleep(interval + 5)
            
        except Exception as e:
            print(f"请求失败: {e}")
            
        # 显示等待提示
        remaining = int(expires_in - (time.time() - start_time))
        if remaining % 15 == 0:  # 每15秒显示一次
            print(f"等待中... 剩余时间: {remaining}秒")
            
        time.sleep(interval)
    
    return None

def main():
    """主函数"""
    show_instructions()
    
    # 获取凭据
    client_id, client_secret = get_credentials()
    if not client_id or not client_secret:
        return
    
    # 获取设备代码
    device_data = get_device_code(client_id)
    if not device_data:
        print("获取设备代码失败，请检查网络连接和 Client ID")
        return
    
    device_code = device_data["device_code"]
    user_code = device_data["user_code"]
    verification_url = device_data["verification_url"]
    expires_in = device_data["expires_in"]
    interval = device_data["interval"]
    
    print("\n" + "=" * 60)
    print("授权信息:")
    print("=" * 60)
    print(f"验证网址: {verification_url}")
    print(f"PIN 码: {user_code}")
    print(f"有效期: {expires_in // 60} 分钟")
    print("=" * 60)
    
    # 获取输出路径
    output_path = input("请输入输出文件路径 [默认: token.json]: ").strip() or "token.json"
    
    # 轮询获取令牌
    token_data = poll_for_token(device_code, interval, expires_in, client_id, client_secret)
    
    if token_data:
        print("\n" + "=" * 60)
        print("成功获取访问令牌!")
        print("=" * 60)
        print(f"Access Token: {token_data['access_token']}")
        print(f"Refresh Token: {token_data['refresh_token']}")
        print(f"有效期: {token_data['expires_in']} 秒 (~90天)")
        
        # 保存令牌
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(token_data, f, indent=4, ensure_ascii=False)
            print(f"\n令牌已保存到: {output_path}")
            print("您可以在其他工具中使用此令牌文件进行认证")
        except Exception as e:
            print(f"保存令牌失败: {e}")
    else:
        print("\n获取访问令牌失败")
        print("可能的原因:")
        print("- 未在浏览器中完成授权")
        print("- PIN 码已过期")
        print("- 网络连接问题")
        print("请重新运行程序重试")

if __name__ == "__main__":
    main()
