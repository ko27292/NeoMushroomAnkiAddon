import json
from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *
from anki.hooks import addHook

import os
import random
import time
from aqt import gui_hooks
from PyQt6.QtCore import pyqtSignal 
from aqt.sound import play
from datetime import datetime, date
from .deck_helper_functions import get_root_deck_id, deck_tree_is_done

ADDON_PATH = os.path.dirname(__file__)
BACKGROUND_DIR = os.path.join(ADDON_PATH, "gardenBackgrounds")
NMK_DIR = os.path.join(ADDON_PATH, "split")
WITHERED_DIR = os.path.join(ADDON_PATH, "withered")
SOUNDS_DIR = os.path.join(ADDON_PATH, "sounds")
ITEMS_DIR = os.path.join(ADDON_PATH, "items")

CURRENT_GARDEN_FILE = os.path.join(ADDON_PATH, "currentGarden.json")
USER_DATA_FILE = os.path.join(ADDON_PATH, "userData.json")
SETTINGS_FILE = os.path.join(ADDON_PATH, "settings.json")

shroomNames = os.listdir(NMK_DIR)

def get_config():
    return mw.addonManager.getConfig(__name__)

class Shroomgarden(QDialog):
    def __init__(self, parent=None):
        super(Shroomgarden, self).__init__(parent)
        self.setWindowTitle("Shroomgarden Add-on")
        self.nmk_labels = []
        self.canvas = None

    def load_nmks(self):
        # remove old NMKs
        for lbl in self.nmk_labels:
            lbl.setParent(None)
            lbl.deleteLater()
        self.nmk_labels.clear()

        with open(CURRENT_GARDEN_FILE, "r") as f:
            garden_data = json.load(f)

        for coordsStr, nmk_data in garden_data["gardenNMKs"].items():
            pixmap = QPixmap(os.path.join(NMK_DIR, nmk_data["nmk"]))
            # scale down non-fully grown mushrooms
            if nmk_data["nmk"] != "nmk_s000.webp":
                pixmap = pixmap.scaled(int(pixmap.width() * 0.75),
                                    int(pixmap.height() * 0.75),
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
            lbl = ClickableLabel(self.canvas, coordsStr)
            lbl.setPixmap(pixmap)
            
            # centre the image on x,y coord
            lbl.move(nmk_data["x"] - pixmap.width() // 2, nmk_data["y"] - pixmap.height() // 2)
            # make sure lower rows are on top 
            if nmk_data.get("upperRow", False) is False:
                lbl.raise_()
            
            lbl.show()
            lbl.clicked.connect(self.load_nmks)
            self.nmk_labels.append(lbl)

        self.update()

    def test_click(self):
        test_card_review()
        self.load_nmks()
        

    def refresh(self):
        self.repaint()
        self.update()

class MenuWindow(QDialog):
    def __init__(self, parent=None):
        super(MenuWindow, self).__init__(parent)
        self.setWindowTitle("Shroomgarden Menu")
        self.canvas = None
        self.resize(400, 300)
        self.layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        self.currentPageNumber = 1
        with open(USER_DATA_FILE, "r") as f:
            self.user_data = json.load(f)

        self.pages = [list(self.user_data["collectedMushrooms"].items())[i:i+4] for i in range(0, len(self.user_data["collectedMushrooms"]), 4)]
        self.create_index()
        self.create_inventory()
        self.create_settings()

        self.setLayout(self.layout)
        
    def create_index(self):
        indexWidget = QWidget()
        layout = QFormLayout(indexWidget)
    
        self.indexActionsBar = QHBoxLayout()
        self.pageCounter = QLabel(f"Page number: 1/{len(self.pages)}")
        self.previousPageButton = QPushButton("Previous Page")
        self.nextPageButton = QPushButton("Next Page")

        self.previousPageButton.clicked.connect(self.previous_page_click)
        self.nextPageButton.clicked.connect(self.next_page_click)

        self.indexActionsBar.addWidget(self.pageCounter)
        self.indexActionsBar.addWidget(self.previousPageButton)
        self.indexActionsBar.addWidget(self.nextPageButton)
        layout.addRow(self.indexActionsBar)

        self.indexLayout = QFormLayout()
        self.load_index_page(self.currentPageNumber)
        layout.addRow(self.indexLayout)

        self.tabs.addTab(indexWidget, "Index")
        
    def load_index_page(self, pageNum):
        # clear existing layout
        for i in reversed(range(self.indexLayout.count())):
            widgetToRemove = self.indexLayout.itemAt(i).widget()
            self.indexLayout.removeWidget(widgetToRemove)
            widgetToRemove.setParent(None)

        # load new page
        if len(self.pages) == 0:
            return
        
        current_page = self.pages[pageNum - 1]
        for nmkName, count in current_page:
            pixmap = QPixmap(os.path.join(NMK_DIR, nmkName))
            pixmap = pixmap.scaled(int(pixmap.width() * 0.75),
                                    int(pixmap.height() * 0.75),
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
            nmk = QLabel()
            nmk.setPixmap(pixmap)
            self.indexLayout.addRow(nmk, QLabel(str(count)))

        self.pageCounter.setText(f"Page number: {pageNum}/{len(self.pages)}")

    def next_page_click(self):
        if self.currentPageNumber < len(self.pages):
            self.currentPageNumber += 1
            self.load_index_page(self.currentPageNumber)
    
    def previous_page_click(self):
        if self.currentPageNumber > 1:
            self.currentPageNumber -= 1
            self.load_index_page(self.currentPageNumber)

    def create_inventory(self):
        inventoryWidget = QWidget()
        layout = QFormLayout(inventoryWidget)
        shieldRow = QHBoxLayout()
        boosterRow = QHBoxLayout()
        layout.addRow(QLabel("Inventory Items:"))
        
        self.shieldLabel = QLabel()
        shieldPixMap = QPixmap(os.path.join(ITEMS_DIR, "shield.webp"))
        self.shieldLabel.setPixmap(shieldPixMap.scaled(int(shieldPixMap.width() * 0.5),
                                                int(shieldPixMap.height() * 0.5), 
                                                Qt.AspectRatioMode.KeepAspectRatio, 
                                                Qt.TransformationMode.SmoothTransformation
                                                ))
        self.shieldCount = QLabel(str(self.user_data["inventory"].get("shield", 0)))

        self.boosterLabel = QLabel()   
        boosterPixMap = QPixmap(os.path.join(ITEMS_DIR, "booster.webp"))
        self.boosterLabel.setPixmap(boosterPixMap.scaled(int(boosterPixMap.width() * 0.5),
                                                int(boosterPixMap.height() * 0.5), 
                                                Qt.AspectRatioMode.KeepAspectRatio, 
                                                Qt.TransformationMode.SmoothTransformation
                                                ))
        self.boosterCount = QLabel(str(self.user_data["inventory"].get("booster", 0)))
        

        def use_item(item):
            if self.user_data["inventory"].get(item, 0) > 0:
                self.user_data["inventory"][item] -= 1
                with open(USER_DATA_FILE, "w") as f:
                    json.dump(self.user_data, f)
                with open(CURRENT_GARDEN_FILE, "r") as f:
                    garden_data = json.load(f)
                if item == "shield":
                    garden_data["shield"] += 1
                    self.shieldCount.setText(str(self.user_data["inventory"].get("shield", 0)))
                elif item == "booster":
                    garden_data["booster"] += 10
                    self.boosterCount.setText(str(self.user_data["inventory"].get("booster", 0)))

                with open(CURRENT_GARDEN_FILE, "w") as f:
                    json.dump(garden_data, f)

                showInfo(f"Used one {item}.")
                
            else:
                showInfo(f"No {item} left in inventory.")

        useShieldButton = QPushButton("Use Shield")
        useShieldButton.clicked.connect(lambda: use_item("shield"))
        shieldRow.addWidget(self.shieldLabel)
        shieldRow.addWidget(self.shieldCount)
        shieldRow.addWidget(useShieldButton)

        useBoosterButton = QPushButton("Use Booster")
        useBoosterButton.clicked.connect(lambda: use_item("booster"))
        boosterRow.addWidget(self.boosterLabel)
        boosterRow.addWidget(self.boosterCount)
        boosterRow.addWidget(useBoosterButton)
        layout.addRow(shieldRow)
        layout.addRow(boosterRow)

        self.tabs.addTab(inventoryWidget, "Inventory")

    def create_settings(self):
        settingsWidget = QWidget()
        rootLayout = QVBoxLayout(settingsWidget)
        themesLayout = QHBoxLayout()
        rootLayout.addLayout(themesLayout)

        leftLayout = QFormLayout()
        themesLayout.addLayout(leftLayout)
        self.selectThemeMenu = QMenu()
        
        themes = list(get_config()["gardenPositions"].keys())
        for theme in themes:
            action = QAction(theme, self.selectThemeMenu)
            self.selectThemeMenu.addAction(action)

        leftLayout.addRow(QLabel("Select Garden Theme:"))
        self.selectThemeButton = QPushButton("Select Theme")
        self.selectThemeButton.setMenu(self.selectThemeMenu)
        leftLayout.addRow(self.selectThemeButton)
        
        rightLayout = QVBoxLayout()
        themesLayout.addLayout(rightLayout)
        imageLabel = QLabel()
        imageLabel.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        rightLayout.addWidget(imageLabel)
        collectedCount = QLabel()
        rightLayout.addWidget(collectedCount)

        rightLayout.addStretch()


        def on_menu_hovered(self, action):
            theme = action.text()
            
            gardenPixMap = QPixmap(os.path.join(BACKGROUND_DIR, theme))
            imageLabel.setPixmap(gardenPixMap.scaled(int(gardenPixMap.width() * 0.25)
                                                , int(gardenPixMap.height() * 0.25)
                                                , Qt.AspectRatioMode.KeepAspectRatio
                                                , Qt.TransformationMode.SmoothTransformation
                                                ))
            
            collectedTheme = [k for k in self.user_data["collectedMushrooms"].keys() if theme.split("_")[0] in k]
            themeShrooms = [k for k in shroomNames if theme.split("_")[0] in k]

            collectedCount.setText(f"Collected {len(collectedTheme)}/{len(themeShrooms)}.")
            
        def on_menu_about_to_hide():
            imageLabel.clear() 
            collectedCount.clear()
            
        def on_triggered(action):
            theme = action.text()
            # update current garden file
            with open(CURRENT_GARDEN_FILE, "r") as f:
                garden_data = json.load(f)
            garden_data["gardenName"] = theme
            with open(CURRENT_GARDEN_FILE, "w") as f:
                json.dump(garden_data, f)

            gardenPixMap = QPixmap(os.path.join(BACKGROUND_DIR, theme))
            imageLabel.setPixmap(gardenPixMap.scaled(int(gardenPixMap.width() * 0.25)
                                                , int(gardenPixMap.height() * 0.25)
                                                , Qt.AspectRatioMode.KeepAspectRatio
                                                , Qt.TransformationMode.SmoothTransformation
                                                ))
            
            collectedTheme = [k for k in self.user_data["collectedMushrooms"].keys() if theme.split("_")[0] in k]
            themeShrooms = [k for k in shroomNames if theme.split("_")[0] in k]

            collectedCount.setText(f"Collected {len(collectedTheme)}/{len(themeShrooms)}.")
            showInfo(f"Garden theme changed to {theme}.")

        self.selectThemeMenu.hovered.connect(lambda action: on_menu_hovered(self, action))
        self.selectThemeMenu.aboutToHide.connect(on_menu_about_to_hide)
        self.selectThemeMenu.triggered.connect(on_triggered)

        # add the settings options
        settingsLayout = QVBoxLayout()
        rootLayout.addLayout(settingsLayout)

        settings = load_settings()

        reviewsPerNMKSpin = QSpinBox()
        reviewsPerNMKSpin.setMinimum(2)
        reviewsPerNMKSpin.setValue(settings["reviewsPerNMK"]) 
        settingsLayout.addWidget(QLabel("Reviews per Mushroom Growth:"))
        settingsLayout.addWidget(reviewsPerNMKSpin)

        gardenShowIntervalSpin = QSpinBox()
        gardenShowIntervalSpin.setMinimum(30)
        gardenShowIntervalSpin.setValue(settings["gardenShowInterval"])
        settingsLayout.addWidget(QLabel("Cards between Garden Shows:"))
        settingsLayout.addWidget(gardenShowIntervalSpin)

        commonChanceSpin = QDoubleSpinBox()
        commonChanceSpin.setMinimum(0.6)
        commonChanceSpin.setMaximum(1.0)
        commonChanceSpin.setSingleStep(0.1)
        commonChanceSpin.setValue(settings["common_chance"])
        settingsLayout.addWidget(QLabel("Common Mushroom Chance:"))
        settingsLayout.addWidget(commonChanceSpin)

        shieldRatioSpin = QDoubleSpinBox()
        shieldRatioSpin.setMinimum(0.0)
        shieldRatioSpin.setMaximum(1.0)
        shieldRatioSpin.setSingleStep(0.1)
        shieldRatioSpin.setValue(settings["shieldRatio"])
        settingsLayout.addWidget(QLabel("Shield vs Booster Ratio:"))
        settingsLayout.addWidget(shieldRatioSpin)

        rewardsThresholdSpin = QSpinBox()
        rewardsThresholdSpin.setMinimum(20)
        rewardsThresholdSpin.setValue(settings["rewardsThreshold"])
        settingsLayout.addWidget(QLabel("Rewards Threshold:"))
        settingsLayout.addWidget(rewardsThresholdSpin)

        saveSettingsButton = QPushButton("Save Settings")
        def save_settings_click():
            new_settings = {
                "reviewsPerNMK": reviewsPerNMKSpin.value(),
                "gardenShowInterval": gardenShowIntervalSpin.value(),
                "common_chance": commonChanceSpin.value(),
                "shieldRatio": shieldRatioSpin.value(),
                "rewardsThreshold": rewardsThresholdSpin.value()
            }
            with open(SETTINGS_FILE, "w") as f:
                json.dump(new_settings, f)
            showInfo("Settings saved.")

        saveSettingsButton.clicked.connect(save_settings_click)
        settingsLayout.addWidget(saveSettingsButton)

        self.tabs.addTab(settingsWidget, "Settings")

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def __init__(self, parent, coordsStr):
        super(ClickableLabel, self).__init__(parent)
        self.coordsStr = coordsStr

    def mousePressEvent(self, event):
        with open(CURRENT_GARDEN_FILE, "r") as f:
            garden_data = json.load(f)

        with open(USER_DATA_FILE, "r") as f:
            user_data = json.load(f)


        nmkName = garden_data["gardenNMKs"][self.coordsStr]["nmk"]
        if nmkName == "nmk_s000.webp": # if not grown
            play(os.path.join(SOUNDS_DIR, "NEO_SE_cry_child.ogg"))
            return
        
        play(os.path.join(SOUNDS_DIR, "NEO_SE_cry_normal.ogg"))
        play(os.path.join(SOUNDS_DIR, "NEO_SE_nmk_fall.ogg"))
        # if collected before, increment count
        if user_data["collectedMushrooms"].get(nmkName, None):
            user_data["collectedMushrooms"][nmkName] += 1
        else:
            user_data["collectedMushrooms"][nmkName] = 1
        
        del garden_data["gardenNMKs"][self.coordsStr]
        
        

        with open(CURRENT_GARDEN_FILE, "w") as f:
            json.dump(garden_data, f)

        with open(USER_DATA_FILE, "w") as f:
            json.dump(user_data, f)

        self.clicked.emit()

def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)
    return settings
    
def show_menu():
    dialog = MenuWindow(mw)
    dialog.setWindowTitle("Shroomgarden Menu")
    dialog.exec()

def show_shroomgarden():
    dialog = Shroomgarden(mw)
    dialog.setWindowTitle("Shroomgarden")

    layout = QVBoxLayout()
    canvas = QWidget(dialog)
    dialog.canvas = canvas

    with open (CURRENT_GARDEN_FILE, "r") as f:
        garden_data = json.load(f)
    
    garden = QPixmap(os.path.join(BACKGROUND_DIR, garden_data["gardenName"]))
    garden_label = QLabel(canvas)
    
    garden_label.setPixmap(garden)
    w = garden.width()
    h = garden.height()
    
    dialog.setFixedSize(w + 20, h + 50)

    layout.addWidget(canvas)
    dialog.load_nmks()
    dialog.setLayout(layout)
    dialog.exec()

def get_available_positions(gardenName, occupied_positions):
    cfg = get_config()
    gardenPosInfo = cfg["gardenPositions"][gardenName]
    positions = []
    upperRow = []
    if gardenPosInfo["hasMulti"] is False:
        tl, width, height = gardenPosInfo.get("spawnArea", [])
        upperRow.append(tl[1])
        num_rows = height // 40
        num_cols = width // 80
        for row in range(num_rows):
            for col in range(num_cols):
                x = tl[0] + col * 80 + row%2 * 40 # HCP style offset between rows
                y = tl[1] + row * 40
                positions.append((x, y))
    
    if gardenPosInfo["hasMulti"] is True:
        for area in gardenPosInfo.get("spawnAreas", []):
            tl, width, height = area
            upperRow.append(tl[1])
            num_rows = height // 40
            num_cols = width // 80
            for row in range(num_rows):
                for col in range(num_cols):
                    x = tl[0] + col * 80 + row%2 * 40 # HCP style offset between rows
                    y = tl[1] + row * 40
                    positions.append((x, y))
    
    # use sets to remove the occupied positions from available positions
    availablePositions = list(set(positions) - set(occupied_positions))
    
    return availablePositions, upperRow

def grow_new_nmk(garden_data, occupied_positions):
    gardenName = garden_data["gardenName"]
    availablePositions, upperRow = get_available_positions(gardenName, occupied_positions)
    
    if availablePositions:
        spawnPos = random.choice(availablePositions)
        garden_data["gardenNMKs"][f"{spawnPos[0]}_{spawnPos[1]}"] = {"nmk": "nmk_s000.webp", "x": spawnPos[0], "y": spawnPos[1], "stage": 0}
        if spawnPos[1] in upperRow:
            garden_data["gardenNMKs"][f"{spawnPos[0]}_{spawnPos[1]}"]["upperRow"] = True

        with open(CURRENT_GARDEN_FILE, "w") as f:
            json.dump(garden_data, f)
        

def on_question_show(card):
    mw._q_start_time = time.time()

def on_show_answer(ease):
    mw._a_start_time = time.time()

def on_answer_card(reviewer, card, ease):
    now = time.time()
    mw._a_end_time = now

    settings = load_settings()

    total_time = now - mw._q_start_time

    with open(CURRENT_GARDEN_FILE, "r") as f:
        garden_data = json.load(f)

    with open(USER_DATA_FILE, "r") as f:
        user_data = json.load(f)

    # change theme if all mushrooms are collected
    theme = garden_data["gardenName"].split("_")[0]
    themeShrooms = [k for k in shroomNames if theme in k]
    userShrooms = user_data["collectedMushrooms"].keys()
    gardenFull = False

    if set(themeShrooms).issubset(set(userShrooms)): 
        availableThemes = list(get_config()["gardenPositions"].keys())
        ind = availableThemes.index(garden_data["gardenName"]) + 1
        if ind < len(availableThemes):
            newTheme = availableThemes[ind]
            garden_data["gardenName"] = newTheme
        

    # check if the mushrooms should wither
    if total_time > 90 and garden_data["cardsCompleted"] is False and garden_data["shield"] == 0:
        numberWithers = total_time // 90
        
        # get only the grown mushrooms
        grown_nmks = {
            k: v for k, v in garden_data["gardenNMKs"].items()
            if isinstance(v.get("stage"), int) and v["stage"] == (settings["reviewsPerNMK"] - 1)
            }
        
        # select sample of random mushrooms to wither
        selected = random.sample(list(grown_nmks.items()), min(numberWithers, len(list(grown_nmks.items()))))
        theme = garden_data["gardenName"].split("_")[0]
        witheredShroom = [k for k in shroomNames if theme in k]
        for coordsStr, nmk_data in selected:
            garden_data["gardenNMKs"][coordsStr]["nmk"] = witheredShroom[random.randint(0, len(witheredShroom)-1)]
            garden_data["gardenNMKs"][coordsStr]["stage"] = settings["reviewsPerNMK"]

    elif total_time > 90 and garden_data["shield"] > 0:
        garden_data["shield"] -= 1  # shield protects from withering once

    # prevent withering when deck is completed
    root_id = get_root_deck_id(card.did)
    if deck_tree_is_done(root_id):
        garden_data["cardsCompleted"] = True
    else:
        garden_data["cardsCompleted"] = False

    # get all the current occupied spots for mushrooms
    existing_nmks = garden_data["gardenNMKs"]
    occupied_positions = []
    for nmkdata in existing_nmks.values():
        occupied_positions.append((nmkdata["x"], nmkdata["y"]))

    if occupied_positions == []: # no currently growing mushrooms
        grow_new_nmk(garden_data, occupied_positions)

    elif random.random() < 0.3: # 30% chance to start growing a new mushroom
        grow_new_nmk(garden_data, occupied_positions)

    else:
        # randomly select an existing mushroom to grow
        ungrown_nmks = {
            k: v for k, v in garden_data["gardenNMKs"].items()
            if isinstance(v.get("stage"), int) and v["stage"] < (settings["reviewsPerNMK"] - 1)
            }
        if not ungrown_nmks:
            gardenFull = True
            return  # all mushrooms are fully grown
        select = random.choice(list(ungrown_nmks.keys()))
        garden_data["gardenNMKs"][select]["stage"] += 1

        # get theme mushrooms
        theme = garden_data["gardenName"].split("_")[0]
        themeShrooms = [k for k in shroomNames if theme in k]

        # set the chance for common depending on whether boost is active
        if garden_data["booster"] > 0:
            common_chance = max(0.2, settings["common_chance"] - 0.3)  # increase rare chance by 30%
            garden_data["booster"] -= 1
        else:
            common_chance = settings["common_chance"]

        # if the stage is greater than the configured review count, transform it into a grown mushroom
        if garden_data["gardenNMKs"][select]["stage"] > settings["reviewsPerNMK"] - 2:
            if random.random() < common_chance:
                commonShrooms = [k for k in themeShrooms if "s001" in k]
                newShroom = random.choice(commonShrooms)
            else: 
                rareShrooms = [k for k in themeShrooms if "s001" not in k]
                newShroom = random.choice(rareShrooms)
            
            garden_data["gardenNMKs"][select]["nmk"] = newShroom


    if garden_data["cardCount"] > (settings["gardenShowInterval"] - 1) or gardenFull is True:
        garden_data["cardCount"] = 0
        show_shroomgarden()
    
    else:
        garden_data["cardCount"] += 1

    # reward shield after accumulating 200 easy answers
    if ease == 3:
        garden_data["easyCount"] += 1 
        if garden_data["easyCount"] >= settings["rewardsThreshold"]:
            garden_data["easyCount"] = 0
            if random.random() < settings["shieldRatio"]:  # adjustable ratio between shield and booster
                user_data["inventory"]["shield"] = user_data["inventory"].get("shield", 0) + 1
                showInfo("You have earned a shield! You can use it to protect your mushrooms from withering once. Check your inventory from Mushroom Menu to use!")
            else:
                user_data["inventory"]["booster"] = user_data["inventory"].get("booster", 0) + 1
                showInfo("You have earned a booster! You can use it to increase spawn rate of rare mushrooms. Check your inventory from Mushroom Menu to use!")


    with open(CURRENT_GARDEN_FILE, "w") as f:
        json.dump(garden_data, f)

    with open(USER_DATA_FILE, "w") as f:
        json.dump(user_data, f)

gui_hooks.reviewer_did_show_question.append(on_question_show)
gui_hooks.reviewer_did_show_answer.append(on_show_answer)
gui_hooks.reviewer_did_answer_card.append(on_answer_card)


action = mw.form.menuTools.addAction("Show Mushroom Menu")
action.triggered.connect(show_menu)


