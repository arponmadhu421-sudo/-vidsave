from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile

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
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [
                {'format_id': 'best', 'quality': 'Best Quality (Video)', 'ext': 'mp4'},
                {'format_id': 'worst', 'quality': 'Low Quality (Video)', 'ext': 'mp4'},
                {'format_id': 'bestaudio', 'quality': 'MP3 Audio Only', 'ext': 'mp3'},
            ]
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
    quality = data.get('quality', '')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            if quality == 'MP3 Audio Only':
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(tmpdir, 'audio.%(ext)s'),
                    'quiet': True,
                }
            else:
                # This gets video WITH audio combined
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'outtmpl': os.path.join(tmpdir, 'video.%(ext)s'),
                    'quiet': True,
                    'merge_output_format': 'mp4',
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

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
