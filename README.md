This project is a small script designed to help manual captioning of an image database. It requires python and Pillow if you use source code.
![Software Screenshot](./example/Example.png)

## Installation
First, clone this repo
```
git clone https://github.com/Wylgrif/Captioninghelper
```
Then you need python with this library to run this code
```
pip install pillow pyqt5
```
Run Main .py to use this programm.
You must have Ollama with Lava(or another vision llm) to use the autocaptioning feature.

## Informations
1.Main.py:<br/>
  Main.py is the app. You can run it and use it. You can change the language with the gear logo (English and French).<br/>
2.Metattxt.py:<br/>
  Metatxt.py is another app which you can use to extract the image prompt generated with Automatic1111. It is in french only for the momment.<br/>
