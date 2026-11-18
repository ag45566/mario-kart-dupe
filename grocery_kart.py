"""Shopper Kart: a first-person grocery store racing game using Tkinter."""

import math
import time
import tkinter as tk


WIDTH, HEIGHT = 960, 640
ROUND_SECONDS = 120
INK = "#201833"
PINK = "#ff4f9a"
BLUE = "#38c7f4"
YELLOW = "#ffe34f"
GREEN = "#59dc8a"
PURPLE = "#a65cf4"
ORANGE = "#ff824a"

GROCERIES = [
    ("Strawberries", "#ff5968", -0.58),
    ("Milk", "#f7fbff", 0.00),
    ("Bread", "#d68a46", 0.58),
    ("Cheese", "#ffd64b", -0.48),
    ("Bananas", "#ffdc4a", 0.53),
    ("Carrots", "#ff9146", 0.00),
]

THEMES = [
    {"name": "KAWAII FREEZERIA", "sky": "#ffc6e8", "track": "#f578ba", "edge": "#ffe7f5", "shelf": "#9e5bbd", "accent": "#fff06a", "sign": "SWEET SCOOPS + SNACKS", "bend": 34, "turn": 0.018},
    {"name": "ADVENTURE MARKET", "sky": "#8be0a5", "track": "#e8903f", "edge": "#ddf2b0", "shelf": "#72533d", "accent": "#58e9e0", "sign": "JUNGLE JUNCTION", "bend": 58, "turn": 0.013},
    {"name": "MOONLIGHT MYSTERY", "sky": "#6869b8", "track": "#514e9f", "edge": "#cbd7ff", "shelf": "#383755", "accent": "#65f2ec", "sign": "MOON MART", "bend": 48, "turn": 0.024},
    {"name": "HAUNTED HOUSE SHOP", "sky": "#6d4b79", "track": "#4e3859", "edge": "#dac3e4", "shelf": "#34283e", "accent": "#a8ed59", "sign": "BOO! BODEGA", "bend": 65, "turn": 0.021},
]


class ShopperKart:
    def __init__(self, root):
        self.root = root
        root.title("Shopper Kart! — grocery store grand prix")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                highlightthickness=0, bg="#ffc6e8")
        self.canvas.pack()
        self.keys = set()
        root.bind("<KeyPress>", self.key_down)
        root.bind("<KeyRelease>", self.key_up)
        self.round_number = 1
        self.start_round()
        self.tick()

    def start_round(self):
        self.theme = THEMES[(self.round_number-1) % len(THEMES)]
        self.player_distance = 0.0
        self.player_x = 0.0
        self.player_speed = 7.4
        self.boost_active = False
        self.items = [
            {"name": name, "color": color, "lane": lane, "distance": 42 + i*56,
             "index": i, "got": False}
            for i, (name, color, lane) in enumerate(GROCERIES)
        ]
        self.powerups = [
            {"kind": "magnet", "distance": 145.0, "lane": -0.72, "got": False},
            {"kind": "star", "distance": 285.0, "lane": 0.05, "got": False},
        ]
        self.magnet_until = 0
        self.star_until = 0
        self.obstacles = [
            {"distance": 70+i*56, "lane": lane, "kind": kind, "hit": False}
            for i,(lane,kind) in enumerate(((0.42,"spill"),(-0.42,"cart"),(0.38,"spill"),(-0.4,"cart"),(0.4,"spill"),(-0.35,"cart")))
        ]
        self.trick_charges = 1
        self.slow_until = 0
        self.steer_lock_until = 0
        self.player_hit_until = 0
        self.grab_until = 0
        self.grabbed_item = None
        self.grab_point = (WIDTH/2, 515)
        self.peel_effect = None
        self.rivals = [
            {"name": "MOMO", "color": PINK, "distance": 26.0, "speed": 8.0,
             "lane": -0.55, "bag": 0, "next_pickup": 58.0, "flash": 0, "stunned_until": 0, "boost_until": 0, "next_boost": 6},
            {"name": "KAI", "color": PURPLE, "distance": 50.0, "speed": 8.4,
             "lane": 0.54, "bag": 0, "next_pickup": 106.0, "flash": 0, "stunned_until": 0, "boost_until": 0, "next_boost": 9},
            {"name": "LULU", "color": GREEN, "distance": -12.0, "speed": 7.7,
             "lane": -0.24, "bag": 0, "next_pickup": 44.0, "flash": 0, "stunned_until": 0, "boost_until": 0, "next_boost": 12},
            {"name": "BEAN", "color": ORANGE, "distance": 75.0, "speed": 8.2,
             "lane": 0.22, "bag": 0, "next_pickup": 131.0, "flash": 0, "stunned_until": 0, "boost_until": 0, "next_boost": 15},
        ]
        self.started = time.monotonic()
        self.finished = None
        self.message = "GRAB THE GROCERIES. BEAT THE SHOPPERS TO CHECKOUT!"
        self.message_until = time.monotonic()+3
        self.keys.clear()
        self.draw()

    def key_down(self, event):
        key = event.keysym.lower()
        if key == "r" and self.finished:
            self.round_number += 1
            self.start_round()
            return
        if key == "f" and key not in self.keys and not self.finished:
            self.use_banana_trick()
        self.keys.add(key)

    def key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def remaining(self):
        return max(0, ROUND_SECONDS-int(time.monotonic()-self.started))

    def tick(self):
        now=time.monotonic()
        if not self.finished:
            dt=1/60
            steer=("right" in self.keys or "d" in self.keys) - ("left" in self.keys or "a" in self.keys)
            if now < self.steer_lock_until:
                steer=0
            self.player_x=max(-0.88,min(0.88,self.player_x+steer*1.25*dt))
            self.player_speed=self.speed_from_controls()
            if now < self.slow_until:
                self.player_speed=min(self.player_speed,3.2)
                self.boost_active=False
            self.player_distance += self.player_speed*dt
            self.move_rivals(dt)
            self.check_obstacles()
            self.collect_powerups()
            self.collect_groceries()
            if all(item["got"] for item in self.items):
                self.finished="win"
            elif any(r["bag"] == len(GROCERIES) for r in self.rivals):
                self.finished="lose"
            elif self.remaining()==0:
                self.finished="time"
        self.draw()
        self.root.after(16,self.tick)

    def speed_from_controls(self):
        """Space gives the player's kart a strong, visible speed boost."""
        self.boost_active="space" in self.keys
        if "down" in self.keys or "s" in self.keys:
            self.boost_active=False
            speed=4.6
        elif self.boost_active:
            speed=15.5
        elif "up" in self.keys or "w" in self.keys:
            speed=10.3
        else:
            speed=8.1
        if time.monotonic() < self.star_until:
            speed+=3.2
        return speed

    def move_rivals(self, dt):
        for i,rival in enumerate(self.rivals):
            now=time.monotonic()
            if rival["bag"] < len(GROCERIES):
                target_lane=GROCERIES[rival["bag"]][2]
            else:
                target_lane=0
            # They look for the next grocery, but swerve around hazards on the way.
            for obstacle in self.obstacles:
                obstacle_gap=obstacle["distance"]-rival["distance"]
                if 0 < obstacle_gap < 18 and abs(target_lane-obstacle["lane"])<0.38:
                    target_lane=0.82 if obstacle["lane"]<0 else -0.82
                    break
            lane_step=1.3*dt
            rival["lane"] += max(-lane_step,min(lane_step,target_lane-rival["lane"]))
            player_gap=rival["distance"]-self.player_distance
            if player_gap < -16 and now >= rival["next_boost"]:
                rival["boost_until"]=now+1.25
                rival["next_boost"]=now+7
            if now >= rival["stunned_until"]:
                pace=rival["speed"]
                if player_gap < -28:
                    pace+=1.4
                elif player_gap > 48:
                    pace-=0.7
                if now < rival["boost_until"]:
                    pace+=3.0
                rival["distance"] += pace*dt
            if now >= rival["stunned_until"]:
                for obstacle_index,obstacle in enumerate(self.obstacles):
                    if obstacle_index in rival.setdefault("hit_obstacles", set()):
                        continue
                    if abs(obstacle["distance"]-rival["distance"]) < 0.55 and abs(obstacle["lane"]-rival["lane"]) < 0.22:
                        rival["hit_obstacles"].add(obstacle_index)
                        rival["stunned_until"]=now+0.8
                        rival["flash"]=now+0.8
                        rival["distance"]=max(0,rival["distance"]-2.0)
                        break
            if (rival["bag"] < len(GROCERIES)
                    and rival["distance"] >= rival["next_pickup"]
                    and abs(rival["lane"]-GROCERIES[rival["bag"]][2]) < 0.34):
                rival["bag"] += 1
                rival["flash"] = time.monotonic()+1.5
                rival["next_pickup"] += 56
                if rival["bag"] < len(GROCERIES):
                    self.message=f"{rival['name']} grabbed {GROCERIES[rival['bag']-1][0]}!"
                    self.message_until=time.monotonic()+1.5

    def collect_groceries(self):
        for item in self.items:
            if item["got"]:
                continue
            gap=item["distance"]-self.player_distance
            lane_range=1.4 if time.monotonic()<self.magnet_until else 0.28
            if -1.2 <= gap <= 1.4 and abs(self.player_x-item["lane"]) < lane_range:
                item["got"]=True
                self.grabbed_item=item["name"]
                self.grab_until=time.monotonic()+0.65
                self.grab_point=self.project(item["lane"]-self.player_x,gap)[:2]
                self.message=f"YOU GRABBED {item['name'].upper()}!"
                self.message_until=time.monotonic()+1.6
                if item["name"]=="Bananas":
                    self.trick_charges+=1
                    self.message="BANANAS! +1 PEEL TRICK — PRESS F!"
            elif gap < -2:
                # Missed groceries circle back farther up the course for another try.
                item["distance"]=self.player_distance+76

    def collect_powerups(self):
        now=time.monotonic()
        for powerup in self.powerups:
            if powerup["got"]:
                continue
            gap=powerup["distance"]-self.player_distance
            if -1.2 <= gap <= 1.4 and abs(self.player_x-powerup["lane"])<0.32:
                powerup["got"]=True
                if powerup["kind"]=="magnet":
                    self.magnet_until=now+8
                    self.message="MAGNET ON! IT PULLS GROCERIES IN FROM THE SIDE!"
                else:
                    self.star_until=now+6
                    self.message="STAR POWER! SPEED BOOST FOR 6 SECONDS!"
                self.message_until=now+2
            elif gap < -2:
                powerup["distance"]=self.player_distance+90

    def check_obstacles(self):
        now=time.monotonic()
        for obstacle in self.obstacles:
            if obstacle["hit"]:
                continue
            gap=obstacle["distance"]-self.player_distance
            if -1.0 <= gap <= 1.3 and abs(self.player_x-obstacle["lane"])<0.33:
                obstacle["hit"]=True
                self.player_distance=max(0,self.player_distance-1.6)
                self.player_x=max(-0.88,min(0.88,self.player_x+(0.22 if self.player_x<=obstacle["lane"] else -0.22)))
                self.slow_until=now+1.9
                self.steer_lock_until=now+0.38
                self.player_hit_until=now+0.85
                hazard="WET FLOOR!" if obstacle["kind"]=="spill" else "CART CRASH!"
                self.message=f"{hazard} SPUN OUT — SPEED + PROGRESS LOST!"
                self.message_until=now+1.5
            elif gap < -2:
                obstacle["hit"]=True

    def use_banana_trick(self):
        if self.trick_charges <= 0:
            self.message="NO BANANA PEELS! GRAB BANANAS FOR ANOTHER TRICK."
            self.message_until=time.monotonic()+1.5
            return
        target=min(self.rivals,key=lambda rival:abs(rival["distance"]-self.player_distance))
        if abs(target["distance"]-self.player_distance)>90:
            self.message="NO SHOPPER CLOSE ENOUGH FOR THE PEEL!"
            self.message_until=time.monotonic()+1.3
            return
        target["stunned_until"]=time.monotonic()+1.8
        target["distance"]=max(0,target["distance"]-3.0)
        target["flash"]=time.monotonic()+1.8
        self.peel_effect={"target":target,"start":time.monotonic(),"end":time.monotonic()+0.65}
        self.trick_charges-=1
        self.message=f"BANANA PEEL! {target['name']} SPUN OUT!"
        self.message_until=time.monotonic()+1.8

    def road_center(self, y):
        curve=math.sin(self.player_distance*self.theme["turn"])*self.theme["bend"]
        amount=max(0,min(1,(y-220)/390))
        return WIDTH/2+curve*amount

    def road_half(self, y):
        amount=max(0,min(1,(y-220)/390))
        return 135+amount*520

    def draw_track(self):
        c=self.canvas
        t=self.theme
        c.create_rectangle(0,0,WIDTH,HEIGHT,fill=t["sky"],outline="")
        c.create_rectangle(0,0,WIDTH,90,fill=INK,outline="")
        # Store shelves stand at the edges of a wide checkout-race track.
        horizon=220
        c.create_polygon(0,110,345,220,345,575,0,575,fill=t["shelf"],outline=INK,width=3)
        c.create_polygon(WIDTH,110,615,220,615,575,WIDTH,575,fill=t["shelf"],outline=INK,width=3)
        for y in (180,280,390,510):
            end=220+(y-220)*0.32
            c.create_line(0,y,345,end,fill=t["accent"],width=5)
            c.create_line(WIDTH,y,615,end,fill=t["accent"],width=5)
            for side in (-1,1):
                for j in range(6):
                    xx=30+j*50 if side<0 else WIDTH-30-j*50
                    col=(PINK,BLUE,YELLOW,GREEN)[(j+y//100+self.round_number)%4]
                    c.create_rectangle(xx,y-24,xx+20,y-6,fill=col,outline="white",width=1)
        # Track bends gently to make the scene feel like a race course.
        top=self.road_center(horizon)
        bottom=self.road_center(HEIGHT)
        c.create_polygon(top-140,horizon,top+140,horizon,
                         bottom+self.road_half(HEIGHT),HEIGHT,
                         bottom-self.road_half(HEIGHT),HEIGHT,
                         fill=t["track"],outline=t["edge"],width=5)
        # Dashed lane markings scroll toward the kart.
        phase=(self.player_distance*0.8)%1
        for i in range(9):
            p=(i/8+phase/8)%1
            y=horizon+28+p*345
            center=self.road_center(y)
            half=self.road_half(y)
            for lane in (-0.33,0.33):
                x=center+lane*half
                c.create_line(x,y-9,x,y+9,fill="#fff7d8",width=max(2,int(2+p*3)))
        if self.boost_active or time.monotonic()<self.star_until:
            streak_phase=int(self.player_distance*4)%28
            for j in range(6):
                sy=295+((j*47+streak_phase)%250)
                c.create_line(45+j*22,sy,105+j*22,sy-24,fill="#fff7a6",width=3)
                c.create_line(815-j*22,sy,875-j*22,sy-24,fill="#fff7a6",width=3)
        # A checkered finish banner repeats around the loop.
        c.create_rectangle(344,208,616,230,fill="white",outline=INK,width=2)
        for j in range(12):
            col=INK if j%2==0 else "white"
            c.create_rectangle(346+j*22,210,368+j*22,220,fill=col,outline="")
        c.create_rectangle(0,90,WIDTH,90,fill=INK,outline="")
        c.create_text(WIDTH/2,110,text=t["sign"],fill=t["accent"],font=("Arial",12,"bold"))

    def project(self, lane, gap):
        # Larger gap means farther away at the vanishing point.
        depth=max(0.4,gap)
        fraction=max(0,min(1,1-depth/95))
        y=220+fraction*325
        x=self.road_center(y)+lane*self.road_half(y)*0.72
        size=max(0.27,min(1.5,0.30+fraction*1.18))
        return x,y,size

    def draw_obstacles(self):
        c=self.canvas
        for obstacle in self.obstacles:
            if obstacle["hit"]:
                continue
            gap=obstacle["distance"]-self.player_distance
            if gap < -2 or gap > 92:
                continue
            x,y,s=self.project(obstacle["lane"]-self.player_x,gap)
            if obstacle["kind"]=="spill":
                c.create_oval(x-23*s,y-8*s,x+23*s,y+9*s,fill="#62ddff",outline="white",width=max(1,2*s))
                c.create_polygon(x,y-25*s,x-13*s,y-3*s,x+13*s,y-3*s,
                                 fill=YELLOW,outline=INK,width=max(1,s))
                c.create_text(x,y-10*s,text="!",fill=INK,font=("Arial",max(6,int(11*s)),"bold"))
            else:
                c.create_rectangle(x-19*s,y-18*s,x+19*s,y+6*s,fill=ORANGE,outline=INK,width=max(1,2*s))
                c.create_line(x-24*s,y-22*s,x-24*s,y+11*s,fill=INK,width=max(1,3*s))
                for side in (-1,1):
                    c.create_oval(x+(side*15-4)*s,y+3*s,x+(side*15+4)*s,y+12*s,
                                  fill=INK,outline="white",width=max(1,s))

    def draw_powerups(self):
        c=self.canvas
        for powerup in self.powerups:
            if powerup["got"]:
                continue
            gap=powerup["distance"]-self.player_distance
            if gap < -2 or gap > 92:
                continue
            x,y,s=self.project(powerup["lane"]-self.player_x,gap)
            c.create_oval(x-22*s,y-22*s,x+22*s,y+22*s,fill="#fffdf6",outline=YELLOW,width=max(2,3*s))
            if powerup["kind"]=="magnet":
                c.create_line(x-11*s,y-12*s,x-11*s,y+3*s,x-7*s,y+12*s,
                              x,y+15*s,x+7*s,y+12*s,x+11*s,y+3*s,x+11*s,y-12*s,
                              fill=PINK,width=max(3,7*s),smooth=True,capstyle=tk.ROUND)
                c.create_rectangle(x-16*s,y-15*s,x-7*s,y-9*s,fill=BLUE,outline="")
                c.create_rectangle(x+7*s,y-15*s,x+16*s,y-9*s,fill=BLUE,outline="")
                label="MAGNET"
            else:
                points=[]
                for n in range(10):
                    angle=-math.pi/2+n*math.pi/5
                    radius=(17 if n%2==0 else 8)*s
                    points.extend((x+math.cos(angle)*radius,y+math.sin(angle)*radius))
                c.create_polygon(*points,fill=YELLOW,outline=ORANGE,width=max(2,2*s))
                c.create_oval(x-5*s,y-4*s,x-2*s,y+1*s,fill="white",outline="")
                label="STAR"
            c.create_text(x,y+29*s,text=label,fill=INK,font=("Arial",max(7,int(9*s)),"bold"))

    def draw_grocery(self,x,y,name,scale=1):
        c=self.canvas
        s=scale
        def pt(dx,dy): return x+dx*s,y+dy*s
        def oval(dx,dy,rx,ry,fill,outline=INK,w=2):
            c.create_oval(x+(dx-rx)*s,y+(dy-ry)*s,x+(dx+rx)*s,y+(dy+ry)*s,
                          fill=fill,outline=outline,width=max(1,w*s))
        def poly(points,fill,outline=INK,w=2):
            coords=[v for a,b in points for v in pt(a,b)]
            c.create_polygon(*coords,fill=fill,outline=outline,width=max(1,w*s),smooth=True)
        def line(points,fill,w=2,smooth=False):
            coords=[v for a,b in points for v in pt(a,b)]
            c.create_line(*coords,fill=fill,width=max(1,w*s),smooth=smooth,capstyle=tk.ROUND)
        c.create_oval(x-18*s,y-17*s,x+18*s,y+18*s,fill="#fffdf7",outline="#ffd7e8",width=max(1,2*s))
        if name=="Strawberries":
            poly([(-12,-4),(-8,-12),(0,-8),(8,-12),(12,-4),(8,8),(0,15),(-9,8)],"#ff5b71","#c93957")
            poly([(-12,-5),(-5,-11),(0,-6),(5,-12),(12,-5),(5,-3),(0,-6),(-6,-2)],GREEN,"#42a968",1)
            for dx,dy in ((-5,2),(5,2),(-3,8),(3,8),(0,5)): oval(dx,dy,1,1,YELLOW,"",0)
            fy=1
        elif name=="Milk":
            poly([(-10,-8),(-10,13),(10,13),(10,-8),(4,-13),(-4,-13)],"#fffdf8",BLUE)
            poly([(-5,-13),(-3,-18),(4,-18),(6,-13)],BLUE,"#3186bc",1)
            c.create_rectangle(x-9*s,y+5*s,x+9*s,y+10*s,fill="#8de0ff",outline="")
            fy=0
        elif name=="Bread":
            oval(0,1,15,14,"#d99156","#a95e3c")
            oval(0,1,11,10,"#f2c17a","#d99156",1)
            line([(-5,-5),(-2,-1)],"#d99156",2); line([(5,-5),(2,-1)],"#d99156",2)
            fy=3
        elif name=="Cheese":
            poly([(-15,-10),(15,-7),(10,13),(-13,11)],YELLOW,"#d3a52a")
            for dx,dy,r in ((-7,-3,2),(7,-2,2.5),(-7,7,1.8),(8,8,1.8)): oval(dx,dy,r,r,"#edb92d","",0)
            fy=2
        elif name=="Bananas":
            line([(-13,-7),(-8,3),(0,9),(8,6),(13,-5)],"#b66d33",17,True)
            line([(-13,-7),(-8,3),(0,9),(8,6),(13,-5)],"#ffdb50",12,True)
            line([(-8,1),(0,6),(7,4)],"#fff09c",2,True); fy=0
        else:
            poly([(-10,-7),(10,-7),(4,5),(0,16),(-4,5)],"#ff984d","#d66b35")
            poly([(-8,-7),(-13,-14),(-3,-10),(0,-17),(3,-10),(13,-14),(8,-6)],GREEN,"#45ab6a",1)
            fy=-1
        for dx in (-4,4):
            oval(dx,fy,2.5,3,"white",INK,1)
            oval(dx+0.5,fy,1,1.7,INK,"",0)
        for dx in (-8,8): oval(dx,fy+5,2,1.2,"#ff9dac","",0)
        c.create_arc(x-3*s,y+(fy+2)*s,x+3*s,y+(fy+7)*s,start=200,extent=140,
                     style=tk.ARC,outline=INK,width=max(1,s))

    def draw_shopper(self,rival,lane,gap):
        status=""
        if gap < -5 or gap > 110:
            slot=next((i for i,r in enumerate(self.rivals) if r["name"]==rival["name"]),0)
            if gap < -5:
                # Keep trailing racers visible as little trackside/nearby indicators.
                x=72 if slot%2==0 else WIDTH-72
                y=407+(slot//2)*42
                if slot%2:
                    x-=42
                s=0.46
                status="BEHIND"
            else:
                # Racers far ahead stay visible near the distant horizon.
                x=360+slot*78
                y=250+(slot%2)*20
                s=0.34
                status="AHEAD"
        else:
            x,y,s=self.project(lane,gap)
        c=self.canvas
        # Shopper pushes a basket cart; head and body are easy to recognize.
        c.create_oval(x-24*s,y+22*s,x+25*s,y+30*s,fill="#554762",outline="")
        c.create_rectangle(x-13*s,y-1*s,x+13*s,y+23*s,fill=rival["color"],outline=INK,width=max(1,2*s))
        c.create_oval(x-10*s,y-20*s,x+10*s,y+2*s,fill="#ffd1ae",outline=INK,width=max(1,2*s))
        c.create_arc(x-11*s,y-22*s,x+11*s,y-1*s,start=0,extent=180,fill="#3b2847",outline=INK,width=max(1,s))
        for ex in (-4,4):
            c.create_oval(x+(ex-1.5)*s,y-11*s,x+(ex+1.5)*s,y-7*s,fill=PURPLE,outline="")
        c.create_rectangle(x+12*s,y+9*s,x+32*s,y+23*s,fill=YELLOW,outline=INK,width=max(1,s))
        c.create_line(x+10*s,y+7*s,x+14*s,y+7*s,fill=INK,width=max(1,s))
        label=f"{rival['name']}  {rival['bag']}/6"
        if status:
            c.create_rectangle(x-48*s,y+27*s,x+48*s,y+44*s,fill="#fffdf4",outline=INK,width=1)
            label+=f"  {status}"
        c.create_text(x,y+35*s,text=label,fill=INK,
                      font=("Arial",max(6,int(8*s)),"bold"))
        if time.monotonic()<rival["flash"]:
            label="SPUN OUT!" if time.monotonic()<rival["stunned_until"] else "PICKUP!"
            c.create_text(x,y-29*s,text=label,fill=YELLOW,font=("Arial",max(7,int(9*s)),"bold"))
        elif time.monotonic()<rival["boost_until"]:
            c.create_text(x,y-29*s,text="BOOST!",fill=YELLOW,font=("Arial",max(7,int(9*s)),"bold"))
        if time.monotonic()<rival["stunned_until"]:
            c.create_text(x,y-43*s,text="✦  ✦  ✦",fill=YELLOW,font=("Arial",max(8,int(12*s)),"bold"))

    def draw_player_cart(self):
        c=self.canvas
        x=WIDTH/2+self.player_x*185
        # A visible shopper character in a kart makes the player identity obvious.
        if self.boost_active or time.monotonic()<self.star_until:
            for side in (-1,1):
                bx=x+side*48
                c.create_polygon(bx-10,548,bx+10,548,bx+5,570,bx+17,589,
                                 bx,581,bx-16,591,bx-5,568,
                                 fill=YELLOW,outline=ORANGE,width=2)
            c.create_text(x,438,text="STAR BOOST!" if time.monotonic()<self.star_until and not self.boost_active else "BOOST!",
                          fill=YELLOW,font=("Arial",12,"bold"))
        c.create_oval(x-54,557,x+55,576,fill="#554762",outline="")
        c.create_oval(x-41,548,x-21,568,fill=INK,outline="white",width=2)
        c.create_oval(x+21,548,x+41,568,fill=INK,outline="white",width=2)
        c.create_polygon(x-39,529,x+39,529,x+47,558,x-47,558,
                         fill="#ff5b9e",outline=INK,width=3)
        c.create_line(x-31,537,x+31,537,fill="#ffd9eb",width=3)
        # Shopper's blue jacket, arms, face, hair and sparkly eyes.
        c.create_polygon(x-17,493,x+17,493,x+25,530,x-25,530,fill=BLUE,outline=INK,width=2)
        c.create_line(x-15,502,x-34,530,fill=BLUE,width=10,capstyle=tk.ROUND)
        c.create_line(x+15,502,x+34,530,fill=BLUE,width=10,capstyle=tk.ROUND)
        c.create_oval(x-10,481,x+10,503,fill="#ffd2ae",outline=INK,width=2)
        c.create_arc(x-11,478,x+11,497,start=0,extent=180,fill="#352444",outline=INK,width=1)
        c.create_oval(x-6,489,x-3,493,fill=PURPLE,outline="")
        c.create_oval(x+3,489,x+6,493,fill=PURPLE,outline="")
        c.create_text(x,465,text="YOU",fill=INK,font=("Arial",10,"bold"))
        if time.monotonic()<self.player_hit_until:
            c.create_text(x,449,text="SPIN!",fill=ORANGE,font=("Arial",12,"bold"))
        for n,item in enumerate(self.items):
            if item["got"]:
                self.draw_grocery(x-38+n*15,543,item["name"],0.28)
        if time.monotonic()<self.grab_until:
            gx,gy=self.grab_point
            t=1-(self.grab_until-time.monotonic())/0.65
            px=gx+(x-gx)*t
            py=gy+(542-gy)*t
            c.create_line(x-25,511,px,py,fill=BLUE,width=9,capstyle=tk.ROUND)
            c.create_oval(px-6,py-6,px+6,py+6,fill="#ffd2ae",outline=INK,width=1)
            self.draw_grocery(px,py,self.grabbed_item,0.48)

    def draw_player_badge(self):
        c=self.canvas
        c.create_oval(251,9,298,56,fill="#fffdf4",outline=BLUE,width=3)
        c.create_oval(264,17,285,39,fill="#ffd2ae",outline=INK,width=2)
        c.create_arc(262,15,287,37,start=0,extent=180,fill="#352444",outline=INK,width=1)
        c.create_oval(268,26,271,30,fill=PURPLE,outline="")
        c.create_oval(278,26,281,30,fill=PURPLE,outline="")
        c.create_text(274,47,text="YOU",fill=INK,font=("Arial",8,"bold"))

    def draw_rival_panel(self):
        c=self.canvas
        c.create_rectangle(780,96,950,252,fill="#fffdf4",outline=INK,width=2)
        c.create_text(794,106,text="RIVALS",anchor="w",fill=INK,font=("Arial",9,"bold"))
        for i,rival in enumerate(self.rivals):
            cy=128+i*30
            c.create_oval(791,cy-10,813,cy+12,fill=rival["color"],outline=INK,width=1)
            c.create_oval(797,cy-9,807,cy+2,fill="#ffd1ae",outline=INK,width=1)
            c.create_arc(796,cy-11,808,cy,start=0,extent=180,fill="#382541",outline=INK,width=1)
            c.create_text(820,cy-5,text=rival["name"],anchor="w",fill=INK,font=("Arial",8,"bold"))
            c.create_text(936,cy-5,text=f"{rival['bag']}/6",anchor="e",fill=PURPLE,font=("Arial",8,"bold"))
            c.create_rectangle(820,cy+6,936,cy+11,fill="#e6ddea",outline="")
            if rival["bag"]:
                c.create_rectangle(820,cy+6,820+116*rival["bag"]/6,cy+11,fill=rival["color"],outline="")

    def draw(self):
        c=self.canvas
        c.delete("all")
        self.draw_track()
        self.draw_obstacles()
        self.draw_powerups()
        # Rival carts are visible on the course, moving ahead or falling behind.
        for rival in self.rivals:
            gap=rival["distance"]-self.player_distance
            self.draw_shopper(rival,rival["lane"]-self.player_x,gap)
        if self.peel_effect and time.monotonic()<self.peel_effect["end"]:
            effect=self.peel_effect
            target=effect["target"]
            progress=1-(effect["end"]-time.monotonic())/(effect["end"]-effect["start"])
            target_x,target_y,_=self.project(target["lane"]-self.player_x,
                                               target["distance"]-self.player_distance)
            cart_x=WIDTH/2+self.player_x*185
            px=cart_x+(target_x-cart_x)*progress
            py=555+(target_y-555)*progress
            self.draw_grocery(px,py,"Bananas",0.72)
        # Groceries lie along the track. Their size and position show how close they are.
        for item in self.items:
            if item["got"]:
                continue
            gap=item["distance"]-self.player_distance
            if gap < -3 or gap > 100:
                continue
            x,y,s=self.project(item["lane"]-self.player_x,gap)
            c.create_oval(x-21*s,y-20*s,x+21*s,y+21*s,fill="#fffdf5",outline="white",width=max(2,3*s))
            self.draw_grocery(x,y,item["name"],s)

        # HUD panels.
        c.create_rectangle(0,0,310,90,fill=INK,outline="")
        c.create_text(20,22,text="SHOPPER KART!",anchor="w",fill=YELLOW,font=("Arial",20,"bold"))
        c.create_text(20,52,text=f"ROUND {self.round_number}  •  {self.theme['name']}",anchor="w",
                      fill=self.theme["accent"],font=("Arial",10,"bold"))
        c.create_text(20,73,text="ARROWS STEER  •  W GO  •  SPACE BOOST  •  F PEEL",anchor="w",
                      fill="white",font=("Arial",8,"bold"))
        self.draw_player_badge()
        c.create_rectangle(790,0,WIDTH,90,fill=INK,outline="")
        left=self.remaining()
        c.create_text(850,23,text="TIME",fill="white",font=("Arial",9,"bold"))
        c.create_text(850,53,text=f"{left//60}:{left%60:02d}",fill=YELLOW if left>20 else PINK,
                      font=("Arial",23,"bold"))
        c.create_text(922,28,text="RACERS",fill="white",font=("Arial",8,"bold"))
        c.create_text(922,52,text=f"YOU + {len(self.rivals)}",fill=self.theme["accent"],font=("Arial",8,"bold"))
        self.draw_rival_panel()

        # List stays visible, but the road and rivals remain the focus.
        c.create_rectangle(12,104,220,260,fill="#fffdf4",outline=INK,width=2)
        c.create_text(28,121,text="PICKUP LIST",anchor="w",fill=INK,font=("Arial",11,"bold"))
        for i,item in enumerate(self.items):
            yy=147+i*18
            mark="✓" if item["got"] else "○"
            c.create_text(28,yy,text=mark,anchor="w",fill=GREEN if item["got"] else "#a399a6",
                          font=("Arial",10,"bold"))
            c.create_text(48,yy,text=item["name"],anchor="w",fill=INK if not item["got"] else "#99909c",
                          font=("Arial",9,"overstrike" if item["got"] else "normal"))
        c.create_text(480,103,text="CHECKOUT GRAND PRIX",fill=INK,font=("Arial",12,"bold"))
        c.create_text(480,123,text=f"GROCERIES {sum(i['got'] for i in self.items)}/6",fill=INK,
                      font=("Arial",9,"bold"))
        active=[]
        if time.monotonic()<self.magnet_until:
            active.append(f"MAGNET {int(self.magnet_until-time.monotonic())+1}s")
        if time.monotonic()<self.star_until:
            active.append(f"STAR {int(self.star_until-time.monotonic())+1}s")
        power_text=f"F PEEL x{self.trick_charges}  •  " + ("  ".join(active) if active else "MAGNET + STAR ICONS")
        c.create_text(480,140,text=power_text,fill=PURPLE,font=("Arial",8,"bold"))
        if time.monotonic()<self.message_until and not self.finished:
            c.create_rectangle(315,152,645,184,fill="#fffdf4",outline="")
            c.create_text(480,168,text=self.message,fill=PURPLE,font=("Arial",10,"bold"))
        self.draw_player_cart()
        if time.monotonic()<self.player_hit_until:
            c.create_rectangle(340,396,620,430,fill=YELLOW,outline=INK,width=2)
            c.create_text(480,413,text="SPUN OUT! SPEED + PROGRESS LOST!",fill=INK,
                          font=("Arial",10,"bold"))
        if self.finished:
            self.draw_end()

    def draw_end(self):
        c=self.canvas
        c.create_rectangle(0,0,WIDTH,HEIGHT,fill=INK,stipple="gray50",outline="")
        c.create_rectangle(220,210,740,420,fill="#fffdf4",outline=self.theme["accent"],width=4)
        if self.finished=="win":
            title,sub,color="CART FULL! YOU WIN!","You beat the other shoppers to checkout.",GREEN
        elif self.finished=="lose":
            title,sub,color="THEY GOT THERE FIRST!","Momo or Kai filled their cart before you.",PINK
        else:
            title,sub,color="TIME'S UP!","The checkout race is over.",ORANGE
        c.create_text(480,270,text=title,fill=color,font=("Arial",25,"bold"))
        c.create_text(480,324,text=sub,fill=INK,font=("Arial",14))
        c.create_text(480,372,text="PRESS R FOR THE NEXT STORE + RACE",fill=PURPLE,font=("Arial",12,"bold"))


if __name__ == "__main__":
    app=tk.Tk()
    ShopperKart(app)
    app.mainloop()
