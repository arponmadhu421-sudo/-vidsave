from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

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
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            seen = set()
            for f in info.get('formats', []):
                height = f.get('height')
                ext = f.get('ext')
                if height and ext == 'mp4' and height not in seen:
                    seen.add(height)
                    formats.append({
                        'format_id': f['format_id'],
                        'quality': f'{height}p',
                        'ext': ext
                    })
            formats.sort(key=lambda x: int(x['quality'].replace('p','')), reverse=True)
            formats.append({'format_id': 'bestaudio/best', 'quality': 'MP3 Audio', 'ext': 'mp3'})
            return jsonify({
                'title': info.get('title', 'Video'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
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
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                    }],
                    'quiet': True,
                }
            else:
                ydl_opts = {
                    'format': f'{format_id}+bestaudio/best',
                    'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                    'quiet': True,
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if quality == 'MP3 Audio':
                    filename = filename.rsplit('.', 1)[0] + '.mp3'

                if os.path.exists(filename):
                    return send_file(filename, as_attachment=True)
                else:
                    files = os.listdir(tmpdir)
                    if files:
                        return send_file(os.path.join(tmpdir, files[0]), as_attachment=True)
                    return jsonify({'error': 'File not found'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
