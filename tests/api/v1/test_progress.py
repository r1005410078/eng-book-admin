#!/usr/bin/env python3
"""
测试异步视频处理进度更新
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_progress_update():
    """测试进度更新"""
    
    # 1. 获取一个视频
    print("1. 获取视频列表...")
    response = requests.get(f"{BASE_URL}/videos/")
    videos = response.json()
    
    if videos["total"] == 0:
        print("❌ 没有视频，请先上传视频")
        return
    
    video = videos["items"][0]
    video_id = video["id"]
    print(f"✅ 找到视频 ID: {video_id}, 标题: {video['title']}")
    
    # 2. 查询初始进度
    print(f"\n2. 查询初始进度...")
    response = requests.get(f"{BASE_URL}/videos/{video_id}/reprocess")
    if response.status_code == 200:
        progress = response.json()
        print(f"✅ 初始状态: {progress['status']}, 进度: {progress['progress']}%")
        print(f"   任务数量: {len(progress['tasks'])}")
        for task in progress['tasks']:
            print(f"   - {task['name']}: {task['status']} ({task['progress']}%)")
    else:
        print(f"❌ 查询失败: {response.status_code} - {response.text}")
        return
    
    # 3. 触发处理（如果还没处理）
    if progress['progress'] == 0 and progress['status'] != 'processing':
        print(f"\n3. 触发视频处理...")
        response = requests.post(f"{BASE_URL}/videos/{video_id}/run_sync?force=true")
        if response.status_code == 202:
            result = response.json()
            print(f"✅ 任务已启动: {result['message']}")
        else:
            print(f"❌ 启动失败: {response.status_code} - {response.text}")
            return
        
        # 4. 轮询进度
        print(f"\n4. 监控进度...")
        max_checks = 30  # 最多检查 30 次
        for i in range(max_checks):
            time.sleep(2)  # 每 2 秒查询一次
            
            response = requests.get(f"{BASE_URL}/videos/{video_id}/reprocess")
            if response.status_code != 200:
                print(f"❌ 查询失败: {response.status_code}")
                break
            
            progress = response.json()
            print(f"\n[{i+1}/{max_checks}] 总进度: {progress['progress']}%, 状态: {progress['status']}")
            
            # 显示每个任务的进度
            for task in progress['tasks']:
                status_icon = "✅" if task['status'] == 'completed' else "🔄" if task['status'] == 'processing' else "⏳"
                print(f"  {status_icon} {task['name']}: {task['status']} ({task['progress']}%)")
            
            # 检查是否完成或失败
            if progress['status'] in ['completed', 'failed']:
                print(f"\n{'✅' if progress['status'] == 'completed' else '❌'} 处理{progress['status']}")
                break
        else:
            print(f"\n⏰ 达到最大检查次数，当前进度: {progress['progress']}%")
    else:
        print(f"\n3. 视频已在处理中或已完成，跳过触发")

if __name__ == "__main__":
    print("=" * 60)
    print("测试异步视频处理进度更新")
    print("=" * 60)
    test_progress_update()
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
