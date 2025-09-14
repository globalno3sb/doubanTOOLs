# -*- coding: utf-8 -*-
"""
主入口文件 - Trakt PIN 码获取工具
"""
from config import get_trakt_app_credentials, get_output_path
from auth import get_device_code, poll_for_token, save_token

def main():
    """主函数"""
    print("Trakt PIN 码获取工具")
    print("=" * 40)
    
    # 获取应用凭据
    client_id, client_secret = get_trakt_app_credentials()
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
    output_path = get_output_path()
    
    # 轮询获取令牌
    token_data = poll_for_token(device_code, interval, expires_in, client_id, client_secret)
    
    if token_data:
        print("\n" + "=" * 60)
        print("成功获取访问令牌:")
        print("=" * 60)
        print(f"Access Token: {token_data['access_token']}")
        print(f"Refresh Token: {token_data['refresh_token']}")
        print(f"有效期: {token_data['expires_in']} 秒 (~90天)")
        
        # 保存令牌
        if save_token(token_data, output_path):
            print(f"\n令牌已保存到: {output_path}")
            print("您可以在其他工具中使用此令牌文件进行认证")
        else:
            print("保存令牌失败")
    else:
        print("\n获取访问令牌失败")
        print("可能的原因:")
        print("- 未在浏览器中完成授权")
        print("- PIN 码已过期")
        print("- 网络连接问题")
        print("请重新运行程序重试")

if __name__ == "__main__":
    main()