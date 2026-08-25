"""
Xbox Play Anywhere 游戏数据获取器
分页获取全部 XPA 游戏，并更新稳定的 data/games.json 文件。
"""

import requests
import json
import os
import uuid
from datetime import datetime
import urllib.parse
import time

def generate_correlation_vector():
    """生成MS-CV (Microsoft Correlation Vector) 头"""
    return f"{uuid.uuid4()}.{uuid.uuid4().hex[:8]}"

def get_xpa_games_page(page_number, results_per_page=50):
    """获取指定页的XPA游戏"""
    
    # API 配置
    api_url = "https://emerald.xboxservices.com/xboxcomfd/browse"
    
    # 构建请求参数，使用正确的分页格式
    params = {
        'locale': 'en-US',
        'ChannelKeyToBeUsedInResponse': 'BROWSE_CHANNELID=_FILTERS=PLAYWITH=XBOXPLAYANYWHERE',
        'Filters': 'eyJQbGF5V2l0aCI6eyJpZCI6IlBsYXlXaXRoIiwiY2hvaWNlcyI6W3siaWQiOiJYYm94UGxheUFueXdoZXJlIn1dfX0=',  # XPA筛选条件
        'PAGENUMBER': str(page_number),
        'RESULTSPERPAGE': str(results_per_page),
        'PLAYWITH': 'XBOXPLAYANYWHERE'
    }
    
    # 生成请求头
    headers = {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
        "x-ms-correlation-id": generate_correlation_vector(),
        "ms-cv": generate_correlation_vector(),
        "origin": "https://www.xbox.com",
        "referer": "https://www.xbox.com/en-US/games/all-games/console?PlayWith=XboxPlayAnywhere"
    }
    
    try:
        response = requests.get(
            api_url,
            params=params,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # 检查是否有分页信息
            if 'channels' in data:
                # 找到正确的channel（修复后的键格式）
                channel_key = f'BROWSE_PAGENUMBER={page_number}&PLAYWITH=XBOXPLAYANYWHERE&RESULTSPERPAGE={results_per_page}'
                if channel_key in data['channels']:
                    channel = data['channels'][channel_key]
                    total_items = channel.get('totalItems', 0)
                    products = channel.get('products', [])
                    
                    # 获取对应的游戏详情
                    if 'productSummaries' in data:
                        return {
                            'success': True,
                            'page': page_number,
                            'total_items': total_items,
                            'games_count': len(products),
                            'games': data['productSummaries']
                        }
                else:
                    # 如果没有找到精确匹配，尝试使用第一个BROWSE开头的键
                    for key in data['channels']:
                        if key.startswith('BROWSE'):
                            channel = data['channels'][key]
                            total_items = channel.get('totalItems', 0)
                            if 'productSummaries' in data:
                                return {
                                    'success': True,
                                    'page': page_number,
                                    'total_items': total_items,
                                    'games_count': len(data['productSummaries']),
                                    'games': data['productSummaries'],
                                    'channel_key_used': key
                                }
            
            return {
                'success': False,
                'error': 'No channel data found',
                'page': page_number
            }
        else:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'page': page_number
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'page': page_number
        }

def process_game_data(game):
    """处理单个游戏数据"""
    try:
        # 确保game是字典类型
        if not isinstance(game, dict):
            return None
        
        # 提取基本信息
        title = game.get('title', '未知游戏')
        
        # 生成游戏URL（使用 slug 格式）
        slug = title.lower()
        slug = slug.replace(' ', '-').replace(':', '').replace("'", "").replace("®", "").replace("™", "")
        slug = slug.replace("---", "-").replace("--", "-")
        url = f"https://www.xbox.com/en-US/games/{slug}"
        
        # 获取发布日期
        release_date = game.get('releaseDate', '')
        if release_date:
            try:
                release_date = datetime.fromisoformat(release_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
            except:
                release_date = release_date[:10] if len(release_date) >= 10 else ''
        
        # 获取图片URL
        image_url = ''
        images_data = game.get('images', {})
        if images_data:
            # 优先使用 boxArt
            box_art = images_data.get('boxArt', {})
            if box_art and 'url' in box_art:
                image_url = box_art['url']
            # 如果没有 boxArt，尝试 hero
            elif 'hero' in images_data and 'url' in images_data['hero']:
                image_url = images_data['hero']['url']
            # 尝试第一个可用的图片
            elif 'superHeroArt' in images_data and 'url' in images_data['superHeroArt']:
                image_url = images_data['superHeroArt']['url']
        
        # 获取评分
        rating = game.get('averageRating', 0)
        
        # 获取分类
        categories = game.get('categories', [])
        
        # 获取开发商和发行商
        developer = game.get('developerName', '')
        publisher = game.get('publisherName', '')
        
        # 获取价格信息
        price = 0
        currency = 'USD'
        specific_prices = game.get('specificPrices', {})
        
        # 处理不同的价格数据结构
        if isinstance(specific_prices, dict):
            # 如果是字典，尝试从purchaseable字段获取价格
            purchaseable = specific_prices.get('purchaseable', [])
            if purchaseable and isinstance(purchaseable, list):
                for price_info in purchaseable:
                    if isinstance(price_info, dict):
                        msrp = price_info.get('msrp', 0)
                        list_price = price_info.get('listPrice', 0)
                        if msrp > 0:
                            price = msrp
                        elif list_price > 0:
                            price = list_price
                        currency = price_info.get('currency', 'USD')
                        break
        elif isinstance(specific_prices, list):
            # 如果是列表，按原来的方式处理
            for price_info in specific_prices:
                if isinstance(price_info, dict) and price_info.get('isMSRP', False):
                    price = price_info.get('amount', 0) / 100
                    currency = price_info.get('currencyCode', 'USD')
                    break
        
        # 创建游戏对象
        game_data = {
            'name': title,
            'title': title,  # 添加title字段
            'image': image_url,
            'url': url,
            'releaseDate': release_date,
            'rating': rating,
            'categories': categories,
            'developer': developer,
            'publisher': publisher,
            'price': price,
            'currency': currency,
            'productId': game.get('productId', ''),
            'availableOn': game.get('availableOn', []),
            'description': game.get('shortDescription', ''),
            'developerName': developer,  # 添加developerName字段
            'publisherName': publisher  # 添加publisherName字段
        }
        
        return game_data
        
    except Exception as e:
        print(f"⚠️  处理游戏数据时出错: {e}")
        return None

def get_all_xpa_games():
    """获取所有XPA游戏（支持分页）"""
    
    print("============================================================")
    print("Xbox Play Anywhere 游戏数据获取器 v5.1")
    print("支持分页获取所有XPA游戏，使用带日期的文件名")
    print("============================================================")
    
    all_games = []
    current_page = 1
    results_per_page = 50
    total_items = 0
    failed_pages = []
    
    # 首先获取第一页来确定总数
    print(f"正在获取第 1 页游戏数据...")
    first_page_result = get_xpa_games_page(current_page, results_per_page)
    
    if not first_page_result['success']:
        error = first_page_result.get('error', 'Unknown error')
        raise RuntimeError(f"获取第1页失败: {error}")
    
    total_items = first_page_result['total_items']
    print(f"✅ 第 1 页获取成功: {first_page_result['games_count']} 个游戏")
    print(f"📊 总共有 {total_items} 个XPA游戏")
    
    # 计算总页数
    total_pages = (total_items + results_per_page - 1) // results_per_page
    print(f"📄 需要获取 {total_pages} 页数据")
    print("============================================================")
    
    # 处理第一页的游戏
    for game in first_page_result['games']:
        processed_game = process_game_data(game)
        if processed_game:
            all_games.append(processed_game)
    
    # 获取剩余页面
    for page in range(2, total_pages + 1):
        print(f"正在获取第 {page}/{total_pages} 页游戏数据...", end=" ")
        
        result = get_xpa_games_page(page, results_per_page)
        
        if result['success']:
            print(f"✅ {result['games_count']} 个游戏")
            
            # 处理游戏数据
            for game in result['games']:
                processed_game = process_game_data(game)
                if processed_game:
                    all_games.append(processed_game)
            
            # 显示进度
            progress = (page / total_pages) * 100
            print(f"进度: {progress:.1f}% | 已获取: {len(all_games)} 个游戏")
            
        else:
            print(f"❌ 失败: {result.get('error', 'Unknown error')}")
            failed_pages.append(page)
        
        # 添加延迟避免请求过快
        time.sleep(0.5)
    
    print("============================================================")
    print(f"✅ 数据获取完成!")
    print(f"📊 成功获取 {len(all_games)} 个游戏")
    print(f"📋 总共处理 {total_pages} 页数据")
    
    if failed_pages:
        print(f"❌ 获取不完整，失败的页面: {failed_pages}")
        raise RuntimeError("部分分页获取失败，保留现有数据文件")

    if not all_games:
        raise RuntimeError("API 未返回任何游戏，保留现有数据文件")
    
    # 保存处理后的数据
    output_data = {
        'totalGames': len(all_games),
        'totalItemsFromAPI': total_items,
        'totalPagesProcessed': total_pages,
        'failedPages': failed_pages,
        'lastUpdated': datetime.now().isoformat(),
        'fetchDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'games': all_games
    }
    
    # 先写临时文件，再原子替换，避免中断时损坏线上数据。
    filename = 'data/games.json'
    temporary_filename = 'data/games.json.tmp'
    with open(temporary_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    os.replace(temporary_filename, filename)
    print(f"✅ 游戏数据已保存到 {filename}")
    
    # 显示数据质量统计
    print("\n数据质量统计:")
    print(f"总游戏数: {len(all_games)}")
    games_with_images = sum(1 for game in all_games if game.get('image'))
    print(f"有图片的游戏: {games_with_images} ({games_with_images/len(all_games)*100:.1f}%)")
    games_with_developer = sum(1 for game in all_games if game.get('developer'))
    print(f"有开发商的游戏: {games_with_developer} ({games_with_developer/len(all_games)*100:.1f}%)")
    games_with_publisher = sum(1 for game in all_games if game.get('publisher'))
    print(f"有发行商的游戏: {games_with_publisher} ({games_with_publisher/len(all_games)*100:.1f}%)")
    
    # 显示前几个游戏示例
    print(f"\n游戏示例 (前10个):")
    for i, game in enumerate(all_games[:10], 1):
        print(f"{i}. {game['name']}")
        print(f"   发布日期: {game['releaseDate']}")
        print(f"   评分: {game['rating']}")
        print(f"   开发商: {game['developer']}")
        print(f"   发行商: {game['publisher']}")
        print(f"   图片: {'有' if game['image'] else '无'}")
        print()
    
    return filename  # 返回保存的文件名

if __name__ == "__main__":
    # 确保data目录存在
    os.makedirs('data', exist_ok=True)
    
    get_all_xpa_games()
