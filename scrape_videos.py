# Do: pip install selenium
# Do: pip install webdriver-manager

# coding:utf8

import os

from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By 
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import argparse
import pandas as pd 


def setup(): 
    option = Options()
    option.add_argument("--incognito")
    option.headless = True
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=option)
    return driver 


def get_youtube_urls(keywords, n, driver=None, omit_videos=[]):
    """
    Search for videos using given keywords 

    Args:
        keywords (str): search keywords, separated by space 
        n (int): no. of videos to search for 
        driver (optional): Selenium webdriver (default is None)
        omit_videos (List[List], optional): list of lists of video titles and video urls to omit from search results (default is [])
    """

    print(f'Searching for videos of "{keywords}" on YouTube')

    if driver is None:
        driver = setup() 

    driver.get(f'https://www.youtube.com/results?search_query={keywords.replace(" ", "+")}')  
    elements = driver.find_elements(By.ID, 'video-title') 

    videos = [] 
    count = 0

    for elem_ in elements:
        url_ = elem_.get_attribute('href')

        # check url exists
        if url_ is None: 
            continue
                
        title_ = elem_.get_attribute('title')

        # check for repeats
        video_ = [title_, url_]

        if video_ not in omit_videos: 
            videos.append(video_)
            count += 1 

            if count >= n: 
                break 

    df = pd.DataFrame(videos, columns=['video_title', 'video_url'])

    return df


def get_bilibili_urls(keywords, n, driver=None, omit_videos=[]): 
    """
    Search for videos using given keywords 

    Args:
        keywords (str): search keywords separated by space 
        n (int): no. of videos to search for 
        driver (optional): Selenium webdriver (default is None)
        omit_videos (List[List], optional): list of lists of video titles and video urls to omit from search results (default is [])
    """

    print(f'Searching for videos of "{keywords}" on bilibili')

    if driver is None:
        driver = setup() 

    driver.get(f'https://search.bilibili.com/all?keyword={keywords.replace(" ", "%20")}')  
    elements = driver.find_elements(By.CLASS_NAME, 'bili-video-card')
    elements = [elem_.find_elements(By.TAG_NAME, 'a')[1] for elem_ in elements]

    videos = [] 
    count = 0
    
    for elem_ in elements:
        url_ = elem_.get_attribute('href')

        # check url exists and url contains video 
        if (url_ is None) | ('video' not in url_): 
            continue
                
        title_ = elem_.get_attribute('text')

        # check for repeats
        video_ = [title_, url_]

        if video_ not in omit_videos: 
            videos.append(video_)

            count += 1 

            if count >= n: 
                break 

    df = pd.DataFrame(videos, columns=['video_title', 'video_url'])

    return df


def new_record(cid_, cls_, count): 
    return {
        'class_id': cid_,
        'class': cls_,
        'count': count,
    }


def get_urls(classes, output_path, num_videos, additional_keywords='', platform='youtube'): 
    """
    Search for videos for given classes 

    Args:
        classes (List): list of classes 
        output_path (str): path to save results to
        num_videos (int or List[int]): no. of videos to search for per class
        additional_keywords (str, optional): additional search keywords to input alongside class, separated by space (default is '')
        platform (str, optional): youtube or bilibili (default is youtube)
    """

    # set up web driver
    driver = setup()

    output_path = Path(output_path)

    # import excel file containing urls. create file if do not already exist
    if os.path.isfile(output_path):
        urls = pd.read_csv(output_path)
    else: 
        urls = pd.DataFrame(columns=['class_id', 'class', 'video_id', 'video_title', 'video_url'])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        urls.to_csv(output_path, index=False, encoding="utf-8-sig")

    # get no. of videos to download by class
    if isinstance(num_videos, int):
        num_videos = [num_videos] * len(classes)
    elif isinstance(num_videos, list):
        assert len(num_videos) == len(classes)
    else: 
        raise TypeError(f"unsupported type: '{type(num_videos)}'")

    # search for videos
    count_tracker = [] # records no. of videos by classes

    for cid_, cls_ in enumerate(classes):
        omit_videos = urls.loc[urls['class_id'] == cid_, ['video_title', 'video_url']].values.tolist()
        n = num_videos[cid_] # total no. of videos to download
        n_exg = len(omit_videos) # no. of existing videos

        if n_exg >= n:
            count_tracker.append(new_record(cid_, cls_, n_exg)) 
            continue
        
        # get additional search keywords 
        keywords = cls_ + ' ' + additional_keywords
        n_new = n - n_exg # no. of new videos to download

        if platform.lower() == 'youtube': 
            urls_by_cls = get_youtube_urls(keywords, n_new, driver, omit_videos)
        elif platform.lower() == 'bilibili': 
            urls_by_cls = get_bilibili_urls(keywords, n_new, driver, omit_videos)
        else:
            raise ValueError('platform not supported')
        
        n = n_exg + len(urls_by_cls) # update n with actual no. of videos downloaded
        urls_by_cls['class_id'] = cid_ 
        urls_by_cls['class'] = cls_
        urls_by_cls['video_id'] = range(n_exg, n)
        urls = pd.concat([urls, urls_by_cls]).reset_index(drop=True)

        count_tracker.append(new_record(cid_, cls_, n)) 

    urls = urls.sort_values(['class_id', 'video_id']).reset_index(drop=True)

    print('================== Output ==================')
    print(urls.head(10))

    # count no. of videos by class  
    print('========== No. of videos by class ==========')
    print(pd.DataFrame.from_records(count_tracker))
    print("============================================")
    
    # export data
    urls.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f'Results saved to {output_path}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('file_path', type=str, help='.txt file containing video classes')
    parser.add_argument('-k', '--additional_keywords', type=str, help='additional search keywords to input alongside video class, separated by space', default='')
    parser.add_argument('-n', '--num_videos', type=int, nargs='+', default=[5], help='no. of videos to search for per class')
    parser.add_argument('-p', '--platform', type=str, help='youtube or bilibili', default='youtube')
    parser.add_argument('-o', '--output_path', type=str, default='data/annotations/urls.csv')

    args = parser.parse_args()

    # get classes 
    with open(args.file_path) as f: 
        classes = f.read().splitlines()
        classes = [cls_.strip(' ') for cls_ in classes]
        classes.sort() 

    # get num videos 
    if len(args.num_videos) == 1:
        num_videos = args.num_videos[0]
    else: 
        assert len(args.num_videos) == len(classes)

    additional_keywords = args.additional_keywords.strip(' ')
    
    # search for videos 
    get_urls(classes, args.output_path, num_videos, additional_keywords=additional_keywords, platform=args.platform)
