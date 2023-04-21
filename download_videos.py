import os
from subprocess import check_output

from pytube import YouTube
from youtube_dl import YoutubeDL

import numpy as np 
import pandas as pd 
import shutil

from argparse import ArgumentParser
from get_urls import new_record

def download_videos(videos, output_root, cap=None, platform='youtube', ext='.mp4'):
    """ Download videos from given platform 
        Parameters:
        ---------------
        videos: pandas DataFrame containing videos to download
        output_root (str): directory to output downloaded videos
        cap (int, optional): max no. of videos to download per class (default is None)
        platform (str, optional): youtube or bilibili
        ext (str, optional): video extension (default is .mp4)
    """
    # create output directory if not already exist
    if not os.path.isdir(output_root): 
        os.makedirs(output_root)

    count_tracker = [] # track no. of videos downloaded by class
    classes = videos[['class_id', 'class']].drop_duplicates().reset_index(drop=True).values.tolist()
    
    for cid_, cls_ in classes:
        videos_by_class = videos[videos['class_id']==cid_]
        count_by_class = sum(videos_by_class['download'])
        
        # create output directory for current class if not already exist
        output_dir = os.path.join(output_root, str(cid_))
        if not os.path.isdir(output_dir): 
            os.makedirs(output_dir)

        # download videos for current class
        # stop at cap if is not None 
        for i, row in videos_by_class.iterrows():
            if cap is not None:
                if count_by_class >= cap:
                    break 

            if row['download']: 
                continue        
            
            if platform == 'youtube':
                download = _download_youtube_video(row['video_url'], row['video_name']+ext, output_dir)
            elif platform == 'bilibili': 
                download = _download_bilibili_video(row['video_url'], row['video_name'], output_dir)
            
            videos.loc[i, 'download'] = download
            count_by_class += download

        count_tracker.append(new_record(cid_, cls_, count_by_class))
        
        # remove output directory for current class if empty
        try:
            os.rmdir(output_dir)
        except: 
            pass
                
    print('======================= Output ========================')
    count = np.sum([ct['count'] for ct in count_tracker])
    print(f'No. of videos downloaded: {count}')
    print('========== No. of videos downloaded by class ==========')
    print(pd.DataFrame.from_records(count_tracker))
    print("=======================================================")

    print('Videos saved to: %s' %output_root) if count > 0 else os.rmdir(output_root)

    return videos


def _download_youtube_video(video_url, video_file, output_dir):
    """ Download videos from youtube
        Parameters:
        ---------------
        video_url (str): URL to download video from
        video_file (str): name to save video file as 
        output_dir (str, optional): path to save videos to 
    """
    try:
        # download video with YoutubeDL
        ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(output_dir, video_file)
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        download = True
        
    except:
        try:
            # download video with pytube
            youtube = YouTube(video_url)
            stream = youtube.streams.get_highest_resolution()
            output = stream.download(output_path=output_dir, filename=video_file)
            download = True

        except Exception as e:
            print(e)
            download = False

    return download


def _download_bilibili_video(video_url, video_file, output_dir):
    """ Download videos from bilibili
        Parameters:
        ---------------
        video_url (str): URL to download video from
        video_file (str): name to save video file as 
        output_dir (str, optional): path to save videos to 
    """
    try:
        check_output(['you-get', '-o', output_dir, '-O', video_file, video_url])
        download = True
    except Exception as e:
        print(e)
        download = False

    return download


def _get_youtube_video_id(video_url):
    """ Extract video id from youtube URL """
    assert 'youtube' in video_url

    host, video_id = os.path.split(video_url)
    if len(video_id) == 0: 
        host, video_id = os.path.split(host)
        
    ss = video_id.find('v=') + len('v=')
    ee = ss + video_id[ss:].find('&')
    video_id = video_id[ss:ee]
    
    return video_id


def _get_bilibili_video_id(video_url):
    """ Extract video id from bilibili URL """
    assert 'bilibili' in video_url

    host, video_id = os.path.split(video_url)
    if len(video_id) == 0: 
        host, video_id = os.path.split(host)

    return video_id


def main(): 
    parser = ArgumentParser()
    parser.add_argument('file', type=str, help='.csv file containing videos to download')
    parser.add_argument('platform', type=str, help='platform to download videos from (youtube/bilibili)')
    parser.add_argument('--cap', type=int, help='cap on no. of videos to download per class')
    parser.add_argument('-o', '--output_path', type=str, default='data/videos')

    args = parser.parse_args()

    # load data 
    videos = pd.read_csv(args.file, encoding='utf-8-sig', low_memory=False)

    assert ('video_url' in videos) & ('class_id' in videos) 

    if 'video_name' not in videos: 
        if args.platform == 'youtube':
            videos['video_name'] = videos['video_url'].apply(_get_youtube_video_id)
        elif args.platform == 'bilibili': 
            videos['video_name'] = videos['video_url'].apply(_get_bilibili_video_id)

    # check if videos are downloaded
    videos['download'] = False

    for class_id in os.listdir(args.output_path):
        for video_file in os.listdir(os.path.join(args.output_path, class_id)): 
            videos.loc[videos['video_name'] == video_file.split('.')[0], 'download'] = True
    
    # download videos 
    if args.platform == 'youtube':
        videos = download_videos(videos, args.output_path, args.cap, platform='youtube')
        videos.to_csv(args.file, encoding='utf-8-sig', index=False)
    elif args.platform == 'bilibili':
        videos = download_videos(videos, args.output_path, args.cap, platform='bilibili')
        videos.to_csv(args.file, encoding='utf-8-sig', index=False)
    else:
        print('Platform not supported. Please try YouTube or Bilibili.')


if __name__ == "__main__":
    main()
