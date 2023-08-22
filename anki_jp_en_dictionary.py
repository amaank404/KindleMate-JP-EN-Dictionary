import argparse
import json
import fnmatch
import zipfile
import os
import shutil
import requests

def cvtjmdictprocessed_to_anki(data: dict) -> bytes:
    # Converting it to Kindle Mate format
    mainfmt = "{word}\t{define}\r\n"
    outdict = []

    i2 = 0
    inc = 25000

    for k, item in data.items():
        if i2 % inc == 0:
            print('-- Processed Words: ', i2)
        
        i2 += 1

        # Readings
        defination = "<div class=readingscont>"
        defination += "・".join([f"<span class=reading>{x}</span>" for x in item["reading"]])
        defination += "</div>"

        # Tags
        defination += f"<div class=tags>{'・'.join(item['tags'])}</div>"

        defination += "<ol>"
        for x in item["definations"]:
            defination += "<li><div class=definecont>"

            # Part of Speech
            if x["partOfSpeech"]:
                defination += f"<div class=definepartspeech>{'・'.join(x['partOfSpeech'])}</div>"

            # English Gloss
            if x["gloss"]:
                defination += "<ul class=gloss>"
                for x1 in x["gloss"]:
                    defination += f"<li>{x1}</li>"
                defination += "</ul>"

            # Field
            if x['field']:
                defination += f"<div class=definefield><b>Fields:</b> <i>{'・'.join(x['field'])}</i></div>"

            # Info
            if x['info']:
                defination += f"<div class=info>Note: {'<br>Note: '.join(x['info'])}</div>"

            # Antonym
            if x['antonym']:
                defination += f"<div class=defineantonym>Antonyms: "
                for i, x1 in enumerate(x["antonym"]):
                    defination += "<span class=defineknji>"
                    if x1['reading']:
                        defination += f"<span class=furigana>{x1['reading']}</span>"
                    defination += f"<span class=knji>{x1['knji']}</span>"
                    defination += "</span>"
                    if i != len(x["antonym"])-1:
                        defination += '・'
                defination += "</div>"

            # Related
            if x['related']:
                defination += f"<div class=definerelated>Related: "
                for i, x1 in enumerate(x["related"]):
                    defination += "<span class=defineknji>"
                    if x1['reading']:
                        defination += f"<span class=furigana>{x1['reading']}</span>"
                    defination += f"<span class=knji>{x1['knji']}</span>"
                    defination += "</span>"
                    if i != len(x["related"])-1:
                        defination += '・'
                defination += "</div>"
            
            defination += "</div></li>"
        
        defination += "</ol>"
        outdict.append(mainfmt.format(word=k, define=defination))
    return ''.join(outdict).encode('utf-8')

def processjmdict(jmdict_data: dict) -> dict:
    outprep = {}
    tags = jmdict_data["tags"]
    for x in jmdict_data["words"]:
        for knji in x["kanji"]:
            entry = {
                "id": x["id"],
                "tags": [tags[y] for y in knji["tags"]],
                "reading": [],
                "definations": [],
            }
            for reading in x["kana"]:
                if "*" in reading["appliesToKanji"] or knji["text"] in reading["appliesToKanji"]:
                    # In case the reading is present
                    entry["reading"].append(reading["text"])
            for define in x["sense"]:
                if not ("*" in define["appliesToKanji"] or knji["text"] in define["appliesToKanji"]):
                    continue
                sentry = {
                    "info": [p for p in define["info"]],
                    "partOfSpeech": [tags[p] for p in define["partOfSpeech"]],
                    "related": [],
                    "antonym": [],
                    "field": [tags[p] for p in define["field"]],
                    "gloss": [p["text"] for p in define["gloss"]]
                }
                for p in define["related"]:
                    if len(p) >= 2:
                        sentry["related"].append(
                            {
                                "knji": p[0],
                                "reading": p[1],
                            }
                        )
                    elif len(p) == 1:
                        sentry["related"].append(
                            {
                                "knji": p[0],
                                "reading": "",
                            }
                        )
                for p in define["antonym"]:
                    if len(p) >= 2:
                        sentry["antonym"].append(
                            {
                                "knji": p[0],
                                "reading": p[1],
                            }
                        )
                    elif len(p) == 1:
                        sentry["antonym"].append(
                            {
                                "knji": p[0],
                                "reading": "",
                            }
                        )
                entry["definations"].append(sentry)
            outprep[knji["text"]] = entry
        for kana in x["kana"]:
            entry = {
                "id": x["id"],
                "tags": [tags[y] for y in kana["tags"]],
                "reading": [],
                "definations": [],
            }
            for define in x["sense"]:
                if not ("*" in define["appliesToKana"] or kana["text"] in define["appliesToKana"]):
                    continue
                sentry = {
                    "info": [p for p in define["info"]],
                    "partOfSpeech": [tags[p] for p in define["partOfSpeech"]],
                    "related": [],
                    "antonym": [],
                    "field": [tags[p] for p in define["field"]],
                    "gloss": [p["text"] for p in define["gloss"]]
                }
                for p in define["related"]:
                    if len(p) >= 2:
                        sentry["related"].append(
                            {
                                "knji": p[0],
                                "reading": p[1],
                            }
                        )
                    elif len(p) == 1:
                        sentry["related"].append(
                            {
                                "knji": p[0],
                                "reading": "",
                            }
                        )
                for p in define["antonym"]:
                    if len(p) >= 2:
                        sentry["antonym"].append(
                            {
                                "knji": p[0],
                                "reading": p[1],
                            }
                        )
                    elif len(p) == 1:
                        sentry["antonym"].append(
                            {
                                "knji": p[0],
                                "reading": "",
                            }
                        )
                entry["definations"].append(sentry)
            outprep[kana["text"]] = entry
    return outprep

def downloadresources():
    resp = requests.get("https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest")

    downloadsurl = {}
    for x in resp.json()["assets"]:
        if (fnmatch.fnmatch(x["name"], "jmdict-eng-?.*.json.zip") or 
            fnmatch.fnmatch(x["name"], "jmnedict-all-?.*.json.zip")):

            print(f"Queing download for asset: `{x['name']}`")
            if x["name"].startswith("jmdict"):
                downloadsurl["jmdict"] = x["browser_download_url"]
            else:
                downloadsurl["jmnedict"] = x["browser_download_url"]

    print()
    for k, v in downloadsurl.items():
        print(f"Downloading {k} from {v}")
        data = requests.get(v).content
        print(f"Writing to disk")
        os.makedirs("data/", exist_ok=True)
        with open(f"data/{k}.zip", 'wb') as fp:
            fp.write(data)
        print(f"Extracting data")
        file = zipfile.ZipFile(f"data/{k}.zip", 'r')
        for x in file.namelist():
            if x.endswith(".json"):
                print("- Found json file within zip, reading it")
                data2 = file.read(x)
                print("- Writing to json file")
                with open(f"data/{k}.json", "wb") as fp:
                    fp.write(data2)
                print("- Extraction Complete, Discarding ZIP File")
                break
        file.close()
        os.remove(f"data/{k}.zip")
        print(f"- Asset Download Complete: `{k}`")

def jmdictRunner():
    print("Processing JMDict - Phase 1")
    print("- Reading and parsing JSON file")
    with open("data/jmdict.json", "rb") as fp:
        jmdict_data = json.loads(fp.read().decode("utf-8"))
    print("- Processing")
    processed_jmdict = processjmdict(jmdict_data)
    print("Processing JMDict - Phase 2")
    print("- Converting JSON Definations to Anki Readable HTML")
    finaldict = cvtjmdictprocessed_to_anki(processed_jmdict)
    print("- Writing to `japanese-dict.txt`")
    with open("japanese-dict.txt", "wb") as fp:
        fp.write(finaldict)
    if os.path.exists(os.path.expanduser("~")+"/Documents/Kindle Mate/dicts"):
        shutil.copyfile("japanese-dict.txt", os.path.expanduser("~")+"/Documents/Kindle Mate/dicts/japanese-dict.txt")
    print("Successfully Processed JMDict")

print("Downloading the latest edition from scriptin/jmdict-simplified")
downloadresources()

print()
print("Starting Processing Phase")
jmdictRunner()