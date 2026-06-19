from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import urllib.request

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "VidSave Backend Running!"

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url', '')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[ext=mp4]/best',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            seen = set()

            for f in info.get('formats', []):
                height = f.get('height')
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')
                ext = f.get('ext', '')

                # Only formats that have BOTH video and audio
                if (height and 
                    vcodec != 'none' and 
                    acodec != 'none' and 
                    ext == 'mp4' and 
                    height not in seen):
                    seen.add(height)
                    formats.append({
                        'format_id': f['format_id'],
                        'quality': f'{height}p',
                        'ext': 'mp4',
                        'url': f.get('url', '')
                    })

            if not formats:
                # Fallback: best combined format
                for f in info.get('formats', []):
                    height = f.get('height')
                    vcodec = f.get('vcodec', 'none')
                    if height and vcodec != 'none' and height not in seen:
                        seen.add(height)
                        formats.append({
                            'format_id': f['format_id'],
                            'quality': f'{height}p',
                            'ext': f.get('ext', 'mp4'),
                            'url': f.get('url', '')
                        })

            formats.sort(key=lambda x: int(x['quality'].replace('p', '')), reverse=True)
            formats.append({
                'format_id': 'bestaudio/best',
                'quality': 'MP3 Audio',
                'ext': 'mp3',
                'url': ''
            })

            return jsonify({
                'title': info.get('title', 'Video'),
                'thumbnail': info.get('thumbnail', ''),
                'formats': formats
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url', '')
    format_id = data.get('format_id', 'best')
    quality = data.get('quality', 'best')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            if quality == 'MP3 Audio':
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                    'quiet': True,
                }
            else:
                # Use best combined format (video+audio in one file)
                ydl_opts = {
                    'format': 'best[ext=mp4]/best[vcodec!=none][acodec!=none]/best',
                    'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                    'quiet': True,
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

                # Find the downloaded file
                files = os.listdir(tmpdir)
                if not files:
                    return jsonify({'error': 'Download failed'}), 500

                filepath = os.path.join(tmpdir, files[0])
                ext = files[0].rsplit('.', 1)[-1] if '.' in files[0] else 'mp4'
                mimetype = 'audio/mpeg' if ext == 'mp3' else 'video/mp4'

                return send_file(
                    filepath,
                    mimetype=mimetype,
                    as_attachment=True,
                    download_name=f'video.{ext}'
                )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
