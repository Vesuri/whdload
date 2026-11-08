# Legends of Valour: player's manual (condensed)

Summary of the SSI rule book (1992), facts only. "(p. N)" is the page number printed in the
rule book. The bestiary booklet "Monstrum Horrendum" has its own page numbers, written
"(MH p. N)". The PDF has two printed pages per PDF page: PDF page 3 holds pp. 1–2, and in
general PDF page k holds pp. 2k−5 and 2k−4, up to p. 60 on PDF page 32. The Mitteldorf Post
(an in-game newspaper with its own pages 1–8) is on PDF pages 5–8.

Notes from the rule book's diagrams, not from its text, are marked *(diagram)*. Notes from
the game code are given with their `hN:OFFSET`.

---

## Quick answers

| Question | Answer |
|---|---|
| How do I eat or drink? | Order a **Feast** at a hostel or inn: click Feast, click a dish to see what it is and what it costs, then click Yes. The Hunger or Thirst bar goes up and the price comes out of your cash (pp. 37–39). Spells can also create food and drink (pp. 52, 55). |
| What is the eye icon at the bottom left? | The **Examine** icon. Click it to inspect the item shown in the Floor window. The result appears in the message window. It gives only a cursory look (pp. 18, 43). |
| What are the three empty rectangles on the left? | The **Unique Magic Items boxes**. They fill only when you find one of the game's three special magic items (p. 18). |
| How do I sleep? | Use the **Rest** icon (Zz) to rest anywhere for 0, 2, 4, 8 or 12 hours (p. 20). For proper sleep, rent a hostel room and use Sleep there (pp. 36–37). If you sleep on the street, you risk arrest for vagrancy and mugging (p. 36). |
| How do I talk to someone? | Face them and click the **Mouth** (Hail) icon (pp. 21, 27). |
| How do I save? | Through the System icon, and only while you are in an inn, tavern or hostel (pp. 17, 23). |
| How do I find where I am? | Click the **Map** icon. A flashing light marks your position (p. 20). |

---

## Box contents and loading (pp. 2, 13)

- The box holds four disks, a data card, a city map and the rule book (p. 2).
- Loading and hard drive installation are on the **Data Card**, not in the rule book (p. 2).
  The rule book says nothing about copy protection.
- After the title sequence, the menu offers **PLAY**, **PLAY NEW GAME**, **DESIGN A
  CHARACTER** and **QUIT** (p. 13).
- Point at an option and left-click it. Right-click normally clears any menu (p. 13).

## Controls (pp. 13, 21, 24–25, 30–31)

The game is mouse-driven and does not support joysticks. The keyboard works, but some
options can be reached only with the mouse (p. 13).

| Input | Effect | Page |
|---|---|---|
| Left-click | Select an icon, menu option or item | 13 |
| Right-click | Clear or close a menu, or leave a screen | 13, 37 |
| Right-click once on the main screen | Enter **Hustle Mode**: moving the mouse left or right turns you, and left-click moves you forward. The manual calls this the fast way to get around. | 24 |
| Cursor Up | Walk forward | 24 |
| Cursor Left / Right | Turn | 24 |
| Cursor keys | Read the rest of a landlord's message when it ends with an arrow sign | 36 |
| Space bar, while moving | Move faster, in any movement style | 24 |
| Space bar, in a fight | Turn 180 degrees so that you can run away | 31 |
| Space bar, with Fireball or Lightning Bolt active | Fire the spell | 52, 55 |
| Enter, at a window | Climb in. Only Thieves' Guild members can do this. | 25, 50 |
| Keyboard | Type your name during character creation (at most 16 letters) | 15 |

---

## Main game screen (pp. 18–22)

The game starts at Mitteldorf's Main Gate (p. 18). Positions below follow the rule book's
labelled diagram on p. 18.

| Position | Element | What it does | Page |
|---|---|---|---|
| Centre | **View window** | Your view of the city | 22, 24 |
| Under the view | **Text bar / message window** | Messages, replies to your questions, item information | 18, 22 |
| Left column, three empty boxes | **Unique Magic Items boxes** | Fill when you find one of the three special magic items | 18 |
| Bottom left, top | **Examine icon** (eye) | Inspect the item shown in the Floor window | 18, 43 |
| Bottom left, middle | **Floor window** | Shows a portable object you are close to. Left-click it to pick it up. | 18–19 |
| Bottom left, bottom | **System icon** (computer) | Opens the options and save/load panel | 19, 23 |
| Bottom, left of centre | **Character Status display** | Seven bars, with the Timer Bar/Box below them | 19, 30 |
| Bottom centre | **Movement Controls** (3×3) | Walk and turn. Also has the Rank icon. | 19, 24 |
| Bottom, right of centre | **Action Controls** (3×3) | Combat, map, spells, rest, use, hail | 20–21 |
| Bottom right | **Compass** | Shows and sets your facing | 21 |
| Right column, top | **Pockets display** | Cash in groats, and six commodity windows | 21–22 |
| Right column, below Pockets | **Backpack** | Six slots | 21 |
| Right column, bottom | **In-Hand display**, with **Throw** (above) and **Drop** (below) | The item in your right hand | 21 |

### Character Status bars (pp. 19, 58)

From left to right. For every bar, higher is better.

| # | Bar | Meaning |
|---|---|---|
| 1 | **General Health** | Overall physical condition. When its cross icon turns green, you have a disease (p. 58). |
| 2 | **Energy** | When it is low, you catch illnesses more easily. Needing rest or food, disease, fighting and casting spells all use it up. |
| 3 | **Combat Injuries** | Falls in fights. Recovering needs a healer and rest. |
| 4 | **Appeal** | The impression you make on the townsfolk. It starts near zero. |
| 5 | **Hunger** | Your need for food |
| 6 | **Thirst** | Your need for drink |
| 7 | **Sleep** | Your need for sleep |

The bars affect each other. Hunger makes you tire faster, and injuries mean you need more
sleep (p. 19). During a fight the display flashes and the bars drop, especially Combat
Injuries (p. 29).

**Timer Bar / Timer Box**, under the bars (pp. 19, 30, 51):
- In a fight, a red line gives a rough idea of your opponent's health.
- It also shows how long a timed spell has left.

### Movement Controls (pp. 19, 24)

*(diagram)* The pad shows these icons:

| | Left | Middle | Right |
|---|---|---|---|
| Top | Turn left | Forward | Turn right |
| Middle | Left arrow | Double forward arrow | Right arrow |
| Bottom | U-turn | Back | **Rank** (square icon) |

The manual names only **Rank**, which opens the Character Screen (p. 19). It is the square
icon at the bottom right: the game's main-panel gadget 25 (`h5:01c8a` calls the character
screen, `h2:0511e`).

### Action Controls (pp. 20–21, 27, 30)

| | Left | Middle | Right |
|---|---|---|---|
| Top: combat | **Crush** | **Thrust** | **Slash** |
| Middle | **Map** | **Magic spells** (mage spell book) | **Priestly spells** (temple spell book) |
| Bottom | **Rest** (Zz) | **Use** (hand) | **Hail** (mouth) |

- **Crush, Thrust, Slash:** attack with the weapon in your hand, or with your fists. See
  Combat.
- **Map:** shows a simplified version of the paper map, with a flashing "You Are Here"
  light. In dungeons it works only as a trail of the places you have visited, which shows the
  way back to the entrance. That trail is lost when you leave, so copy it down if you mean to
  return (p. 20).
- **Magic and Priestly spells:** open your spell books (pp. 20, 51, 53).
- **Rest:** opens a small menu of 0, 2, 4, 8 or 12 hours (p. 20).
- **Use:** uses the item in your hand, if it has a use. Try it on items to find hidden
  purposes (pp. 21, 44).
- **Hail:** calls out "Hey!" to the citizen you are facing, to start a street conversation
  (pp. 21, 27). The manual warns against hailing Trolls.

### Compass (p. 21)

- Shows which way you face.
- Click a point on the rim to face that direction, or drag the pointer round.

### In-Hand display, Backpack and Pockets (pp. 19, 21–22, 44)

- **In-Hand display:** the item in your right hand. The button above it **throws** the item
  and the button below **drops** it (pp. 21, 44).
- **Backpack:** holds up to six items. Click an item to swap it with the one in your hand.
  Click an empty slot to put the hand item there (pp. 21, 44).
- **Pockets:**
  - The top window shows your cash in groats (p. 22).
  - The six windows below are the commodities: Gems, Spices, Pigments, Ore, Hide and Tar
    (p. 21).
  - Click and hold a commodity to see how much of it you carry (p. 22).
  - Cash and commodities you pick up go into Pockets automatically (p. 19).
- Commodity units:

  | Commodity | Unit on p. 21 | Unit on p. 42 |
  |---|---|---|
  | Gems | ounces | ounces |
  | Spices | lbs | pounds |
  | Pigments | pints | pints |
  | Ore | cwts | carats |
  | Hide | pelts | pelts |
  | Tar | kegs | kegs |

  The two pages disagree on the unit for Ore.

### Character Screen (pp. 19–20)

Open it with the Rank icon. It shows your portrait, your rank in each guild and temple you
belong to, and other information that appears as the game goes on.

---

## System (options) panel (p. 23)

Left-click the System icon (the computer, bottom left). *(diagram)* The panel is a 3×3 grid.

| Row | Left | Middle | Right |
|---|---|---|---|
| Top | **Auto-Combat** on/off | **Sound** on/off | **About** Legends of Valour |
| Middle | **Floor** on/off | **Horizon** | **Window** |
| Bottom | **Load Game** | **Save Game** | **Exit** (labelled "Exit to DOS") |

- **Auto Combat:** the computer fights for you, so you need not click the combat icons. It
  does not make you stronger.
- **Sound:** turns music and sound effects on or off.
- **Floor:** switches between texture-mapped and plain floors.
- **Horizon:** moves the viewing horizon nearer or further. A nearer horizon makes the game
  faster.
- **Window:** shrinks the view window.
- The manual says Floor, Horizon and Window can affect speed on slower machines.
- **Save Game** works only in a tavern or hostel and is disabled everywhere else. The text
  on p. 17 also allows inns.

---

## Saving and loading (pp. 16–17, 23)

- You can have up to 8 characters, and so 8 saved games (pp. 16–17).
- A save stores the character, and the save file is named after the character. Another
  character has to start from the beginning (p. 16).
- **New game:** choose PLAY NEW GAME, then pick a character (p. 17).
- **Continue:** PLAY loads your last save. Follow the on-screen instructions (p. 17).
- **Load an earlier save:** choose PLAY, then LOAD GAME on the System panel (p. 17).
- The Saved Game screen lists eight **Chronicles**, one slot per character on the save game
  disk. Click a Chronicle to save to it or load it, and the game continues automatically.
  Saving overwrites the slot (p. 17).
- You can save only in an inn, tavern or hostel (pp. 17, 23).

---

## Character creation (pp. 14–16)

1. Choose **DESIGN A CHARACTER**. The screen shows a full-length picture and a face close-up
   on the left. On the right are a stone tablet with a face, buttons below it, and the raw
   statistics.
2. The four statistics are rolled at random. Left-click **Exit** to roll again if the
   character is too weak. The manual notes that statistics can be improved during play.

   | Statistic | Effect |
   |---|---|
   | **Strength** | Physical power, mainly for combat |
   | **Intelligence** | Reasoning, which helps in various ways |
   | **Speed** | Agility, dexterity and reactions. Affects combat and other areas. |
   | **Health** | Physical robustness |

3. Choose a **Race**:

   | Race | Effect |
   |---|---|
   | Human | Average in everything |
   | Elf | More likely to have high Intelligence and Speed. Weaker Health. |
   | Dwarf | Bonuses to Strength and Health. Lower Speed. |

4. Choose **male** or **female**. Gender does not change the statistics, but it changes how
   people treat you.
5. Change your looks on the **Stone Tablet**. Left-click a facial feature to cycle through
   its styles. The manual suggests starting with hair colour.
6. When you are done, click the **runes** at the bottom of the tablet. Click **Yes** to
   confirm, or **No** to start over.
7. Your home village appears. The message bar gives your father's name and trade. Type your
   name, at most 16 letters.
8. **Buy starting equipment.**
   - Click a village building to learn what it is. Most are shops, and you have a fixed
     amount of money.
   - Left-click a shop to enter it, then left-click an item to see a picture of it with its
     name and price.
   - Click **Buy** to pay and add the item to your character's picture.
   - To skip an item, click another one or click **Exit Shop**.
   - You do not have to spend all your money.
   - p. 29 recommends buying armour in the village.
9. Click the **horizon** to finish. You return to the options screen.

---

## Moving around (pp. 24–25)

You can move with the cursor keys, the Movement icons, the Compass, or Hustle Mode
(right-click once). Hold the space bar to go faster.

- **Doors:** walk into a door to go through it. If nothing happens, you have hit the frame.
- **Locked doors:** the message window says the door is locked. If you have the means to
  batter it down or pick the lock, the game tries that automatically.
- **"Secure" doors:** the door is magically barred. You need magic or a key.
- **Stairs:** walk into them to climb or descend. You have succeeded when the view changes.
- **Windows:** a Thieves' Guild member can walk up to a window and press **Enter** to climb in
  (pp. 25, 50). The **Portal** spell also gets you in. The Watch treats coming in through a
  window as a sign of criminal intent.

---

## Time and the day (pp. 25–26, 34–35)

- A day lasts 24 hours. Citizens give rough times: Before Dawn, About Dawn, Early Morning,
  Mid-Morning, Noon, Mid-Afternoon, Evening and Midnight (p. 35).
- The week has seven days: Moon Day, Tyr's Day, Woden's Day, Thor's Day, Freya's Day, Satyr's
  Day and the Day of the Sun. The seasons change, and days are shorter in autumn (p. 35).
- **Shops** open from about an hour after dawn until an hour before dusk. They are closed on
  the Day of the Sun (p. 34).
- **Inns** open from midday to midnight (p. 34).
- To find the time, ask a citizen ("What is..."), watch the sun, or buy an hourglass (p. 34).
- Nights are dangerous on the streets (pp. 24, 26).
- Hunger, thirst and tiredness grow as time passes. You can starve to death, or become so
  tired that you lose fights you would otherwise win (p. 26).
- Most buildings can be entered (p. 35).

---

## Eating, drinking, sleeping, lodging (pp. 36–39)

### Hostels (pp. 36–38)

- Hostels have a sign outside, shown on p. 36. Several are marked on the paper map, and others
  advertise in the Mitteldorf Post (pp. 36, 38).
- The manual recommends **The Travellers Inn**, the closest to the Main Gate (p. 36).
- Walk forward until you bump the reception desk. The landlord appears with three options
  (p. 36):

  | Option | What it does | Page |
  |---|---|---|
  | **Room** | Shows a floor plan. Click a room to see its weekly rent, then accept or refuse. Accepting takes a week's rent from your cash. There is no credit. | 36 |
  | **Feast** | A menu of food and drink. Click a dish to see what it is and what it costs, then click **Yes** to eat it. | 37–38 |
  | **Exit** | Leave | 38 |

- **Your room** (p. 37):
  - The room stays yours while your rent is paid, and you can pay more than a week ahead.
  - Items you leave in the room are safe.
  - If you fall behind with the rent, the keeper sells your belongings. Unpaid rent is also
    an offence (p. 57).
- **Storing items in the room** (p. 37):
  1. Walk to the **Basket**. It appears in the Floor window.
  2. Click it. Two windows open: Cash & Commodities, and Items.
  3. To store cash or goods, click a Pockets window. Click a basket window to take them back.
  4. To store an item, click an empty basket slot and the item in your right hand goes in. To
     take an item back, click a full slot.
  5. Right-click to leave.
- **Money** kept in your lodgings is completely safe from thieves (p. 34).
- **Sleeping:** in your room, choose **Sleep** and click a number of hours. You may wake a few
  hours earlier or later than you chose (p. 37).
- **Street sleeping:** the Watch arrests you for vagrancy, and Thieves' Guild members mug you
  (p. 36).
- **Hunger and thirst:** eating lowers hunger and drinking lowers thirst. If you neglect them,
  your health suffers (p. 38).
- Right-click leaves any of these screens (p. 38).

### Inns and taverns (pp. 39–40)

- Inns have a sign outside. Examples are the Dragon's Head and the Seahorse Tavern.
- Walk in and bump the counter. The host tells you where you are and offers these options:

  | Option | What it does | Page |
  |---|---|---|
  | **Feast** | Works as at a hostel. Each inn has a different menu, and drinks are a speciality. | 39 |
  | **Notice** | A notice board with **General Info** (sights, activities, deals) and **Work Available** (simple jobs: follow the instructions). Right-click cancels. | 39 |
  | **Gamble** | Card games, shell games and roach racing | 39–40 |

- **Gambling** (p. 40):
  - Most games are played for 1 groat at a time.
  - Shell game: pick the cup with the pea to win 2 groats.
  - Roach racing is at the Hanged Man, with the odds on its notice board.
  - The games vary by tavern and by day of the week.
  - Unpaid gambling debts are an offence (p. 57).

---

## Shops: buying and selling (pp. 22, 41–42)

Enter a shop and bump the counter. The options are **Notice** (as in an inn), **Trade** and
**Exit**.

**Trade screen.** It shows a column of the six commodity icons and four boxes. Each box is
either empty or holds an item.

| Action | Result |
|---|---|
| Click an **empty box** | The keeper offers to buy from you. Click **Yes**, then click an item you carry to hear the price, and accept or refuse. |
| Click a box with an **item** | The keeper tells you its price. Make the deal or not. |
| Click a **commodity** | Shows the buy and sell prices, the shop's stock and how much you carry. Click **Buy** or **Sell** to set the number of units, then **Deal** to complete the trade. |

- Shops resell what you sell them at a higher price, and an item you sold may not stay in
  stock (p. 41).
- Prices vary widely by district and by time (p. 34).
- Pockets show your cash, and holding a commodity shows how much you own (pp. 22, 42).
- Commodities may be held as letters of credit or bills of lading rather than as goods
  (p. 21).
- The currency is the **groat** (p. 34).

---

## Items: finding, examining, using (pp. 18–19, 43–44)

- When you walk over an item it appears in the **Floor window**. Left-click it to pick it up.
  It goes to your right hand if that is empty, otherwise to the Backpack (pp. 19, 43).
- **Examine** (the eye) gives a cursory look, with the result in the message window (p. 43).
- **Reading:** to read a book, put it in your right hand and click it. Scrolls, potion labels
  and some devices work the same way (p. 43).
- Magician's guilds can identify items properly (pp. 43, 51):
  - The Asegeir charge 10g per item.
  - The Loki price varies (Post p. 7).
- Switching an item between hand and backpack shows information about it in the message
  window (p. 44).
- Use the **Throw** and **Drop** buttons for the item in your hand, and the **Use** icon to
  find hidden purposes (p. 44).

---

## Talking (pp. 27–28)

- **In shops and inns:** pick a phrase from the menu. Replies appear in the message area.
- **In the street:** face the person and click the **Mouth** icon ("Hey!"). If they are
  interested, they come over.
- The Conversation Menu:

  | Option | Use |
  |---|---|
  | **Where...** | Pick a place or object from a list. Move the pointer to the top or bottom of the list to scroll. For example, "Where am I?" |
  | **What is...** | Ask the time, the date, or "What is your name?" |
  | **Pick Pocket** | Try to steal from them. This can be illegal (p. 56). |
  | **Insult** | Trade insults. This often turns into a fistfight. |
  | **Attack** | Start a fight at once |
  | **Exit** | End the conversation |

---

## Combat (pp. 29–31)

### Before a fight

- Buy armour and weapons (p. 29).
- Put your weapon in your right hand beforehand by clicking it in the Backpack. You cannot
  search your pack once a fight is under way.
- A non-combat item in your hand when a fight starts drops to the ground.

### When a fight starts

- The other person stops insulting you.
- The Character Status display flashes and the bars start to fall, especially Combat
  Injuries.

### Attacks

| Icon | Attack | Without a weapon |
|---|---|---|
| **Crush** | Downward blow, best with blunt weapons such as maces | Left hook |
| **Slash** | Side-on cut with the edge, best with swords | Right jab |
| **Thrust** | Point-first attack | A combination of punches |

- Click the attack icons as often as you like. Clicks are not buffered: the game waits until
  a blow is finished and then takes your next click.
- Different opponents are weak to different styles. Combinations such as Slash-Slash-Crush
  work very well against some of them. Find them by trial and error.
- Weapons do more damage than fists.
- Red "splats" show your hits.
- The red line in the Timer Box shows roughly how healthy your opponent still is.
- **Throwing:** anything can be thrown. Heavier objects fly a shorter distance but do more
  damage (pp. 30–31).
- **Auto Combat** on the System panel fights for you (p. 23).
- Do not practise attacks in the street, because someone will take it as a challenge (p. 30).

### Running away and training

- Press the **space bar** to turn 180 degrees, then move away (p. 31).
- Warrior guilds train fitness, skill and fortitude (p. 31). The Post advertises:
  - Men-At-Arms: sword and axe training, 5g per week (Post p. 7)
  - Mercenaries: hand-to-hand and weapons training, 10g (Post p. 7)

---

## Health, healing and death (pp. 54, 58–59)

- To stay healthy, eat, drink, sleep in a hostel and avoid getting hit (p. 59).
- Where to get treatment (p. 59):

  | Healer | Notes |
  |---|---|
  | **Town Surgeon** | Found through notice boards and the Mitteldorf Post |
  | **Temple** | Free check-up, expensive treatment. Members pay less. |
  | **Magic** | Heal or Faith Heal spells |

- **Temple Service** (p. 54): the healer checks you and recommends treatment. Conditions
  include dehydration, combat injuries, tomb rot, vampirism and warts.
- A green cross on the Health bar means you have a disease (p. 58).
- **Death** ends the game and returns you to character generation (p. 59).

---

## Guilds (pp. 45–52)

Bump a guild counter for **Business**, **Service** or **Exit** (p. 45).

### Joining and rising (pp. 45–46)

- **Business** offers you membership, unless the guild dislikes you. Guilds and temples are
  rivals, so membership of one can bar you from another.
- Joining costs a fee plus a **challenge**: an errand with a time limit. You may get
  information or help along the way. You can back out. If you pass, you are accepted.
- As a member, **Business** lets you try for the next rank, or resign.
- Guilds pay a small weekly wage. It is paid, with arrears, each time you visit the guild
  counter.
- A rank icon shows your standing in each guild you have joined.
- Higher ranks give access to more **Services**, such as item evaluation and training.
  Members pay less than non-members.

### The guilds

| Guild | Type | Location and notes | Ranks, lowest to highest |
|---|---|---|---|
| **Mercenaries** | Fighters | West side of town. Many gamble at the Roach & Rider Casino, and its bouncers are members. Trains weapons. | Bodyguard's Apprentice, Hireling, Bounty Hunter, Mercenary, Guildmaster (p. 47) |
| **Men-At-Arms** | Fighters | Office in the large barracks on the east side, where wanted posters are printed: avoid it if you are wanted. In good standing with King Farley. Trains weapons. | Grunt, Trooper, Weaponsmith, Captain, Templar (p. 48) |
| **Thieves' Guild** | Thieves | See the notice board in the Twin Snakes Inn by the harbour. The guild stops unlicensed robbery and sets quotas. Training improves lock picking and pocket picking, teaches dodging in combat, and teaches entering buildings through windows (Enter). | Beggar, Pickpocket, Graverobber, Thief, Godfather (pp. 49–50) |
| **Fellowship of the Asegeir** | Magic | Identifies magic items | Spellbrewer's Assistant, Scribe, Spellcaster, Wizard, Wizard Master (p. 51) |
| **Brotherhood of Loki** | Magic | Identifies magic items | Mystic, Sorcerer, Spellbinder, Wizard, Warlock (p. 51) |

### Making money (pp. 45, 39)

- Notice boards in taverns and shops list odd jobs, mostly errands.
- Guilds pay a weekly wage.
- You can trade commodities.
- You can gamble.

---

## Magic (pp. 51–52)

- Joining a magic guild costs a fee and an errand.
- Each grade unlocks stronger spells. They are kept in your spell book, opened with the
  **Magic spells** icon.
- The book lists every spell, but a low grade cannot cast all of them.
- Click a spell's icon to cast it.
- Some spells last for a while, and the **Timer Bar** shows how long is left.
- Spells cost **Energy**. The cost falls as your rank rises.

| Spell | Effect |
|---|---|
| **Portal** | Pass through locked doors, portcullises, windows and barriers, for a limited time |
| **Fireball** | While it is active, the space bar fires |
| **Create Food** | Your right hand must be empty. Eat the food at once with Use, or keep it. |
| **Create Drink** | Creates a drink |
| **Warp** | Teleports you back to the Standing Stones |
| **Heal** | Raises the Health bar to full |
| **Power** | You do more damage. Some monsters can be hurt only with it. |
| **Protection** | You take less damage |

## Temples and priest spells (pp. 53–55)

- The temples are open night and day. Bump the counter for **Business**, **Service** or
  **Exit**.
- **Business:** membership, fees and challenges, and the spell book. Use Business again to
  rise in rank.
- **Service:** a free health check, with paid cures. Members get a discount.
- Cast priest spells with the **Priestly spells** icon.

| Temple | Notes | Ranks, lowest to highest |
|---|---|---|
| **Odin** | Holds a Royal Appointment. In the city centre (Post p. 8). | Neophyte, Magus, Theurgist, Spirit Exorcist, High Priest |
| **Freya** | Women only | Flirt, Coquette, Temptress, Seducer, High Priestess |
| **Aegir** | Meditation | Novice, Theologian, Divine Mediator, Cleric, High Priest |
| **Set** | The snake god | Wriggler, Hisser, Crusher, Striker, Venom Master |

| Priest spell | Effect |
|---|---|
| **Portal** | As the mage spell |
| **Lightning Bolt** | While it is active, the space bar fires |
| **Create Food** | Your right hand must be empty |
| **Create Drink** | Creates a drink |
| **Sanctuary** | Transports you to your temple |
| **Faith Heal** | Raises the Health bar to full |
| **Power** | As the mage spell |
| **Protection** | As the mage spell |

---

## Law and the Watch (pp. 36, 56–57)

- If you are arrested, you go to the Halls of Justice. The court believes the officer, and
  King Farley hears the cases.
- Punishments range from fines to long prison terms. The Post reports 10g fines up to three
  days in prison for vagrancy.
- Fighting Queen Jocasta's case brings a harsher sentence.

| Offence | Notes |
|---|---|
| Acting Suspiciously | |
| Vagrancy | For example, sleeping in the street |
| Excessive Snooping | Looking through other people's windows. Thieves' Guild members and glaziers are licensed to do it. |
| Attempted Robbery | |
| Beastly Behaviour | Turning into a beast |
| Drunk & Disorderly | |
| Assaulting an Officer | Includes killing one |
| Rent Arrears | |
| Gambling Debts | |
| Handling Stolen Goods | |
| Threatening Behaviour | |

---

## Getting lost: maps (pp. 2, 20, 36)

- The box includes a paper city map. Several hostels are marked on it.
- The **Map** icon shows a simpler version of it, with a flashing light at your position.
- **In dungeons**, the map records only where you have been, as a trail back to the entrance.
  The trail is erased when you leave, so copy it if you plan to return.
- To ask someone, use the conversation option **Where... → Where am I?**

## Places mentioned (pp. 34–60 and the Post)

| Place | Notes |
|---|---|
| The Travellers Inn | Hostel nearest the Main Gate (p. 36) |
| Castle Dungeon | Also a hostel (p. 36) |
| Hanged Man | Next to the Standing Stones. Cheap food and beer, and roach racing (p. 40, Post p. 8). |
| Seahorse Tavern | Hosts the beer race (Post p. 6) |
| The Snakes / Twin Snakes Inn | By the harbour (p. 49). The Post says it is a tavern in the south of the city, in the Wetland Wynds. Linked to the thieves. |
| Theatre | You can turn up and get a part (p. 60) |
| Museum | (p. 60) |
| Zoo | East side, near the Main Gate (p. 60) |
| Olaf's Emporium | Next to the theatre (Post p. 8) |
| Rusty Cutlass, healer | South of the Standing Stones and west of the Travellers Inn (Post p. 8) |
| Lamont the Embalmer | Wanlock Tombs, by the West Wall, in Nidavellir (Post p. 8) |
| Asegeir Fellowship | In Newtown, by the castle wall (Post p. 3) |
| Mercenaries headquarters | Witches Meadow, near the Roach and Rider Casino (Post p. 3) |
| Nidavellir | The Dwarves' Ghetto, said to be full of werewolves (Post p. 2) |

The story hook: you have come to find your cousin **Sven**. His letter mentions The Snakes,
the roach races and The Boardins, and his newspaper advert says "contact me at the
Mermaid" (pp. 2–4, Post p. 8).

---

## Monsters (Monstrum Horrendum booklet)

These are the bestiary's practical tips only.

| Monster | Tips |
|---|---|
| Bat | Lives in narrow, low spaces. Disturbing bats may bring goblins or lizard men. Use missiles. |
| Giant Red Bear | Aim for the body and avoid its grip |
| Cyclops | Throws rocks and missiles. Keep clear of it. |
| Demon | Avoid it |
| Dragon | South of the island, beyond the King's hunting lodge, and some in the under-city. Breathes fire. |
| Ghost | Ordinary blades cannot touch it. You need magic. |
| Giant Spider | Strike the eyes. Its bite is poisonous, causing sickness or failing strength. Cure it at a temple, with a leech, or with magic. |
| Goblin | Weak and hunts in packs. Poor eyesight but a keen sense of smell. Its head is hard. |
| Gorgon | Its gaze freezes you and its touch turns your heart to stone. Temples may help. |
| Lizard Man | On the northern beaches. Shy, but fights when cornered. |
| Minotaur | Charges, so it is less dangerous from the side or rear. Fears fire, from a torch or a spell. |
| Mummy | Fears fire, from a torch or a spell. Break it to pieces. |
| Satyr | Some cast magic. Carries treasure. |
| Troll | Its belly is weak. Disarm it or break its limbs. Shuns light. |
| Vampire | The condition is contagious. Symptoms: your skin loses its colour, then you crave raw meat, then blood. |
| Werewolf | Lycanthropy is infectious and shows within a month. Use silvered weapons, spells or wolfsbane. |
| Zombie | Crushes bones and cripples limbs. Plain force of arms works best. Causes flesh-rot. |

The Lamia also appears, without a practical tip.

## Credits (back pages)

- Design: Kevin Bulmer and Ian Downend (US Gold).
- Amiga programming: Graham Lilley and Paul Woakes.
- The rule book is by SSI. SSI's warranty covers defective disks for 30 days.
