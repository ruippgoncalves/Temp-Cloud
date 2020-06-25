import hashlib
import os
import uuid

from cs50 import SQL
from flask import abort, Flask, redirect, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

# Configure the app
app = Flask(__name__)
# Check https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/
app.config["UPLOAD_FOLDER"] = "./upload"
size = 10 * 1024 * 1024
# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///tempCloud.db")


def clean(uuid):
    # Clean DB
    try:
        md5 = db.execute("SELECT md5 FROM files WHERE uuid = :uuid and uploaded < datetime('now', '-1 Hour');",
                         uuid=uuid)

        if not md5:
            return

        # For the improbability of two uuid being equals
        for i in md5:
            # Check file
            temp = db.execute("SELECT uuid FROM files WHERE md5 = :md5 and uploaded >= datetime('now', '-1 Hour');", md5=i["md5"])

            # If it has the same file across multiple downloads
            delete = True
            for i2 in temp:
                if i2["uuid"] != None:
                    delete = False

            # Delete the file if required
            if delete:
                os.remove(app.config["UPLOAD_FOLDER"] + "/" + i["md5"])

                # Delete other downloads for that file that are not required anymore
                db.execute("DELETE FROM files WHERE md5 = :md5 and uploaded < datetime('now', '-1 Hour');", md5=i["md5"])

    except:
        abort(500)

# Index Page
@app.route("/")
def index():
    return render_template("index.html")

# Upload
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        url = request.url_root + "download?item=" + request.args.get("item")

        return render_template("upload.html", url=url)

    # Check if the post request has the file part
    if 'file' not in request.files:
        return redirect("/")
    
    file = request.files['file']
    
    # If nothing was submited
    if file.filename == '':
        return redirect("/")
    
    # Save the file
    originalFilename = secure_filename(file.filename)
    md5 = hashlib.md5(file.read()).hexdigest()
    fileUuid = str(uuid.uuid4())

    # In case of the file already exists
    path = os.path.join(app.config['UPLOAD_FOLDER'], md5)
    if not os.path.exists(path):
        # seek to the beginning of file
        file.stream.seek(0)
        file.save(path)
    
    try:
        db.execute("INSERT INTO files (uuid, md5, name) VALUES (:uuid, :md5, :name);",
                   uuid=fileUuid, md5=md5, name=originalFilename)
    except:
        clean(fileUuid)
        abort(500)

    return redirect("/upload?item=" + fileUuid)

# Download
@app.route("/download")
def download():
    # Check if uuid was provided
    uuid = request.args.get("item")

    if not uuid:
        return redirect("/")
    
    # Clean
    clean(uuid)
    
    # Check if it exists
    try:
        file = db.execute("SELECT md5, name FROM files WHERE uuid = :uuid AND uploaded >= datetime('now', '-1 Hour');",
                          uuid=uuid)
    except:
        abort(500)
    
    try:
        if request.args.get("down") == "wget":
            return redirect(request.url_root + "upload/" + file[0]["md5"])

        return render_template("download.html", name=file[0]["name"], md5=file[0]["md5"], site=request.url)
    except:
        abort(404)

# Uploads directory
@app.route('/upload/<path:path>')
def send_upload(path):
    return send_from_directory(app.config["UPLOAD_FOLDER"], path)


# Error Handler
@app.errorhandler(500)
def err500(error):
    return render_template("500.html"), 500


@app.errorhandler(404)
def err404(error):
    return render_template("404.html"), 404
