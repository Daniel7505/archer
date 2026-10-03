import os
import math
import random
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    WindowProperties, Vec4, Vec3, DirectionalLight, 
    AmbientLight, Spotlight, PerspectiveLens, CardMaker, LineSegs,
    ClockObject
)
from direct.actor.Actor import Actor
from direct.gui.DirectGui import DirectButton, DirectLabel

class PandarenRPGAdventure(ShowBase):
    def __init__(self):
        super().__init__()
        
        # 1. HD Window Viewport Setup
        props = WindowProperties()
        props.set_title("Pandaren RPG Quest: Leveling & Paths")
        props.set_size(1280, 720)
        self.win.request_properties(props)
        
        # 2. Complete 3D Orbit Camera System Setup
        self.disableMouse()
        self.camera_distance = 38.0
        self.camera_heading = 180
        self.camera_pitch = 22
        
        # Core Technical State Trackers
        self.lightning_active_timer = 0.0
        self.shake_intensity = 0.0
        self.lightning_line_node = None
        
        self.stage_pivot = self.render.attachNewNode("StagePivot")
        self.camera.reparentTo(self.stage_pivot)
        self.update_camera_position()
        
        # Animation & Physics Constants
        self.is_dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.base_z_pos = -5.5
        
        # Action States
        self.is_saiyan_active = False
        self.is_jumping = False
        self.jump_time = 0.0
        self.pre_jump_heading = 0.0
        self.kick_hit_done = False
        self.clock = ClockObject.getGlobalClock()
        
        # RPG Player Progress Systems
        self.player_max_hp = 100.0
        self.player_hp = 100.0
        self.player_level = 1
        self.player_xp = 0
        self.xp_needed = 100 # Level up milestone
        self.level_up_alert_timer = 0.0
        
        # WASD Keyboard Input Map
        self.key_map = {"w": 0, "a": 0, "s": 0, "d": 0}
        
        # Input Bindings (Mouse + Actions + WASD)
        self.accept("mouse1", self.start_drag)
        self.accept("mouse1-up", self.stop_drag)
        self.accept("space", self.trigger_jump_kick) 
        self.accept("l", self.shoot_lightning_bolt)   
        self.accept("k", self.toggle_super_saiyan)
        
        self.accept("w", self.set_key, ["w", 1])
        self.accept("w-up", self.set_key, ["w", 0])
        self.accept("s", self.set_key, ["s", 1])
        self.accept("s-up", self.set_key, ["s", 0])
        self.accept("a", self.set_key, ["a", 1])
        self.accept("a-up", self.set_key, ["a", 0])
        self.accept("d", self.set_key, ["d", 1])
        self.accept("d-up", self.set_key, ["d", 0])
        
        # Frame Processing Scheduling Tasks
        self.taskMgr.add(self.orbit_camera_task, "OrbitCameraTask")
        self.taskMgr.add(self.combat_physics_engine, "CombatPhysicsEngine")

        # 3. Load the High-Resolution Pre-Rigged 3D Actor Mesh
        try:
            self.hero = Actor(
                "models/panda-model", 
                {"walk": "models/panda-walk4"}
            )
            self.hero.reparentTo(self.render) 
            self.hero.setPos(0, 0, self.base_z_pos)
            self.hero.setScale(0.0045)
            self.hero.loop("walk")
        except Exception as e:
            print(f"Asset load issue: {e}")
            # Visible stand-in so the game still runs (plain NodePath: no loop())
            self.hero = self.render.attachNewNode("FallbackNode")
            stand_in = self.loader.loadModel("models/misc/sphere")
            stand_in.reparentTo(self.hero)
            stand_in.setScale(1.5)
            stand_in.setZ(1.5)
            self.hero.setPos(0, 0, self.base_z_pos)

        # 4. Built-in Geometric Paths (Stone Walkway Floor Tracks)
        self.path_blocks = []
        for index in range(-4, 5):
            path_tile = self.loader.loadModel("models/misc/sphere")
            path_tile.reparentTo(self.render)
            path_tile.setScale(8.0, 8.0, 0.15)
            # Extends a straight linear path track along the Y-axis
            path_tile.setPos(0, index * 12.0, -5.7)
            path_tile.setColor(Vec4(0.2, 0.2, 0.23, 1)) # Dark grey brick tint
            self.path_blocks.append(path_tile)

        # Grass Arena Surroundings
        self.field = self.loader.loadModel("models/misc/sphere")
        self.field.reparentTo(self.render)
        self.field.setScale(60.0, 60.0, 0.1)
        self.field.setPos(0, 0, -5.8)
        self.field.setColor(Vec4(0.1, 0.15, 0.1, 1))

        # 5. MULTIPLE ACTIVE ENEMY SPAWNING POOL
        self.active_monsters = []
        self.max_monsters_on_field = 4
        self.spawn_monster_wave()

        # 6. Build Procedural Super Saiyan Aura Energy Nodes
        self.aura_particles = []
        for i in range(15):
            cm = CardMaker(f'aura_part_{i}')
            cm.setFrame(-0.8, 0.8, -0.8, 0.8)
            part = self.render.attachNewNode(cm.generate())
            part.setBillboardPointEye() 
            part.setTransparency(True)
            part.setColor(Vec4(1, 0.9, 0, 0.0)) 
            part.setLightOff()
            part.hide()
            self.aura_particles.append(part)

        # 7. Cinematic 3-Point Game Studio Lighting Rig
        self.spot = Spotlight("HeroSpot")
        self.spot.setLens(PerspectiveLens())
        self.spot.setColor(Vec4(0.95, 0.9, 0.85, 1))
        self.spot_np = self.render.attachNewNode(self.spot)
        self.spot_np.setPos(15, -30, 25)
        self.spot_np.lookAt(0, 0, 0)
        self.render.setLight(self.spot_np)

        ambient = AmbientLight("AmbientGlow")
        ambient.setColor(Vec4(0.25, 0.25, 0.28, 1))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)

        # 8. Render Dynamic WoW Interface Elements
        self.setup_ui()

    def spawn_monster_wave(self):
        """Clears old nodes and generates fresh multiple tracking hostiles."""
        for monster in self.active_monsters:
            monster["node"].removeNode()
        self.active_monsters.clear()

        for idx in range(self.max_monsters_on_field):
            golem = self.loader.loadModel("models/misc/sphere")
            golem.reparentTo(self.render)
            golem.setScale(2.0, 2.0, 3.8)
            
            # Scatter enemies at random distances along the path tracks
            golem.setPos(
                random.uniform(-4.0, 4.0), 
                random.uniform(-40.0, -10.0), 
                -3.8
            )
            golem.setColor(Vec4(0.5, 0.1, 0.1, 1))
            
            # Map structural storage details for separate state tracking
            self.active_monsters.append({
                "node": golem,
                "hp": 60.0,
                "max_hp": 60.0
            })

    def set_key(self, key, value):
        self.key_map[key] = value

    def start_drag(self):
        if self.mouseWatcherNode.hasMouse():
            self.is_dragging = True
            self.last_mouse_x = self.mouseWatcherNode.getMouseX()
            self.last_mouse_y = self.mouseWatcherNode.getMouseY()

    def stop_drag(self):
        self.is_dragging = False

    def update_camera_position(self):
        cam_x = 0
        cam_y = -self.camera_distance
        cam_z = 0
        if self.shake_intensity > 0.0:
            cam_x += random.uniform(-self.shake_intensity, self.shake_intensity)
            cam_z += random.uniform(-self.shake_intensity, self.shake_intensity)
        self.camera.setPos(cam_x, cam_y, cam_z)
        # Negative pitch tilts the boom down so the camera sits above the ground
        self.stage_pivot.setHpr(self.camera_heading, -self.camera_pitch, 0)

    def orbit_camera_task(self, task):
        if hasattr(self, 'hero') and self.hero:
            self.stage_pivot.setPos(self.hero.getPos())

        if not self.is_dragging:
            self.camera_heading += 6.0 * self.clock.getDt()
            self.update_camera_position()
        elif self.mouseWatcherNode.hasMouse():
            curr_x = self.mouseWatcherNode.getMouseX()
            curr_y = self.mouseWatcherNode.getMouseY()
            delta_x = curr_x - self.last_mouse_x
            delta_y = curr_y - self.last_mouse_y
            self.camera_heading -= delta_x * 150
            self.camera_pitch = max(-5, min(50, self.camera_pitch + delta_y * 90))
            self.update_camera_position()
            self.last_mouse_x = curr_x
            self.last_mouse_y = curr_y
        return task.cont

    def toggle_super_saiyan(self):
        self.is_saiyan_active = not self.is_saiyan_active
        if self.is_saiyan_active:
            self.hero.setColorScale(Vec4(1.5, 1.3, 0.2, 1.0))
            self.spot.setColor(Vec4(2.0, 1.8, 0.0, 1.0))
            for part in self.aura_particles:
                part.setColor(Vec4(1, 1, 0, 0))
                part.show()
            print("🔥 SUPER SAIYAN MODE ACTIVATED! 🔥")
        else:
            self.hero.clearColorScale()
            self.spot.setColor(Vec4(0.95, 0.9, 0.85, 1))
            for part in self.aura_particles:
                part.setColor(Vec4(1, 1, 0, 0))
                part.hide()

    def trigger_jump_kick(self):
        if not self.is_jumping:
            self.is_jumping = True
            self.jump_time = 0.0
            self.pre_jump_heading = self.hero.getH()
            self.kick_hit_done = False

    def damage_monster(self, monster, dmg):
        """Applies damage and handles the kill + XP reward."""
        monster["hp"] = max(0.0, monster["hp"] - dmg)
        if monster["hp"] <= 0 and monster in self.active_monsters:
            print("💀 MONSTER SLAYED! +25 Experience Points yielded!")
            monster["node"].removeNode()
            self.active_monsters.remove(monster)

            # Gain Experience processing metrics
            self.player_xp += 25
            if self.player_xp >= self.xp_needed:
                self.player_level += 1
                self.player_xp = 0
                self.player_hp = self.player_max_hp # Heal completely
                self.level_up_alert_timer = 2.0 
                print(f"👑 LEVEL UP! Level {self.player_level}! 👑")

    def shoot_lightning_bolt(self):
        if len(self.active_monsters) == 0:
            print("🏰 All enemies dead! Click 'Respawn Monsters' to summon more!")
            return

        # Find the absolute closest enemy target inside our spawning arrays
        h_pos = self.hero.getPos()
        closest_monster = None
        min_dist = 9999.0
        
        for monster in self.active_monsters:
            dist = (h_pos - monster["node"].getPos()).length()
            if dist < min_dist:
                min_dist = dist
                closest_monster = monster

        if not closest_monster:
            return

        if self.lightning_line_node:
            self.lightning_line_node.removeNode()

        segs = LineSegs()
        segs.setThickness(6.0) 
        segs.setColor(Vec4(1, 0.9, 0.2, 1) if self.is_saiyan_active else Vec4(0.2, 0.8, 1, 1))

        enemy_pos = closest_monster["node"].getPos()
        start_point = Vec3(h_pos.getX(), h_pos.getY(), h_pos.getZ() + 3.0)
        end_point = Vec3(enemy_pos.getX(), enemy_pos.getY(), enemy_pos.getZ() + 1.0)
        
        segs.moveTo(start_point)

        segments = 12
        for k in range(1, segments + 1):
            pct = k / segments
            mid_pos = start_point + (end_point - start_point) * pct
            if k < segments:
                mid_pos.setX(mid_pos.getX() + random.uniform(-1.5, 1.5))
                mid_pos.setZ(mid_pos.getZ() + random.uniform(-1.0, 1.0))
            segs.drawTo(mid_pos)  # last step lands exactly on end_point

        geom_node = segs.create()
        self.lightning_line_node = self.render.attachNewNode(geom_node)
        
        self.lightning_active_timer = 0.18 
        self.shake_intensity = 0.55       
        self.spot.setColor(Vec4(3.0, 3.0, 3.0, 1.0))
        
        # Check range constraints context to register damages
        if min_dist < 22.0:
            dmg = 30.0 if not self.is_saiyan_active else 60.0
            print(f"⚡ BLAST HIT! Monster lost {dmg} HP!")
            self.damage_monster(closest_monster, dmg)
        else:
            print(f"💨 Missed! Target too far ({min_dist:.1f} units).")

    def combat_physics_engine(self, task):
        dt = self.clock.getDt()

        # A. WASD Movement Engine Physics Translation Pipeline
        speed = 14.0
        move_x, move_y = 0, 0
        if self.key_map["w"]: move_y += speed * dt  
        if self.key_map["s"]: move_y -= speed * dt  
        if self.key_map["a"]: move_x -= speed * dt
        if self.key_map["d"]: move_x += speed * dt
        
        if (move_x != 0 or move_y != 0) and self.player_hp > 0:
            self.hero.setPos(
                self.hero.getX() + move_x, 
                self.hero.getY() + move_y, 
                self.hero.getZ()
            )
            # Stock panda model faces -Y, so add 180 to face the run direction
            angle = math.atan2(-move_x, move_y) * (180.0 / math.pi) + 180.0
            if self.is_jumping:
                self.pre_jump_heading = angle  # applied on landing
            else:
                self.hero.setH(angle)

        # B. MULTIPLE ENEMY TRACKING AI SWARM
        h_pos = self.hero.getPos()
        for monster in self.active_monsters:
            e_pos = monster["node"].getPos()
            direction = h_pos - e_pos
            direction.setZ(0)  # chase along the ground, don't sink/float
            distance = direction.length()
            
            if distance > 2.2:
                direction.normalize()
                ai_speed = 5.0 if not self.is_saiyan_active else 7.5
                monster["node"].setPos(e_pos + direction * ai_speed * dt)
                monster["node"].lookAt(self.hero)
                monster["node"].setH(monster["node"].getH() + 180) 
            else:
                # Each adjacent golem lands ~1.2 hits per second (5 HP each)
                if random.random() < dt * 1.2:
                    self.player_hp = max(0.0, self.player_hp - 5.0)
                    if self.player_hp <= 0:
                        print("💀 YOU DIED! Resurrecting at path...")
                        self.player_hp = self.player_max_hp
                        self.hero.setPos(0, 0, self.base_z_pos)

        # C. Update Real-Time WoW Interface Health & XP Overlays
        pct_player = max(0.0, self.player_hp / self.player_max_hp)
        pct_xp = max(0.0, self.player_xp / self.xp_needed)
        
        self.ui_p_bar["text"] = (
            f"LVL {self.player_level} PANDA: {self.player_hp:.0f}% HP"
        )
        self.ui_p_bar["frameColor"] = Vec4(
            1.0 - pct_player, pct_player * 0.8, 0, 0.85
        )
        
        self.ui_xp_bar["text"] = f"XP ENGINE BAR: {self.player_xp} / {self.xp_needed}"
        self.ui_xp_bar["frameSize"] = (0, 24 * pct_xp, -0.3, 0.4) 

        # Update closest target health info board
        if len(self.active_monsters) > 0:
            distances = [
                (h_pos - m["node"].getPos()).length() 
                for m in self.active_monsters
            ]
            min_dist = min(distances)
            self.ui_e_bar["text"] = (
                f"SWARM REMAINING: {len(self.active_monsters)} | "
                f"NEAR: {min_dist:.1f}m"
            )
        else:
            self.ui_e_bar["text"] = "DUNGEON CLEARED! Click Respawn Button!"

        # D. Level Up Announcement Strobe Flasher Timer
        if self.level_up_alert_timer > 0.0:
            self.level_up_alert_timer -= dt
            self.ui_level_flash.show()
            self.ui_level_flash["text_fg"] = (1, random.uniform(0.6, 1), 0, 1) 
            if self.level_up_alert_timer <= 0.0:
                self.ui_level_flash.hide()

        # E. Lightning Timers Decay
        if self.lightning_active_timer > 0.0:
            self.lightning_active_timer -= dt
            if self.lightning_active_timer <= 0.0:
                if self.lightning_line_node:
                    self.lightning_line_node.removeNode()
                    self.lightning_line_node = None
                self.spot.setColor(
                    Vec4(2.0, 1.8, 0.0, 1.0) if self.is_saiyan_active 
                    else Vec4(0.95, 0.9, 0.85, 1)
                )

        if self.shake_intensity > 0.0:
            self.shake_intensity = max(0.0, self.shake_intensity - dt * 2.0)
            self.update_camera_position()

        # F. Safe Super Saiyan particle color scaling loop
        if self.is_saiyan_active and self.hero:
            for part in self.aura_particles:
                current_alpha = part.getColor().getW() 
                if current_alpha <= 0.0:
                    part.setPos(
                        h_pos.getX() + random.uniform(-1.5, 1.5), 
                        h_pos.getY() + random.uniform(-1.0, 1.0), 
                        h_pos.getZ() + random.uniform(1.0, 5.0)
                    )
                    part.setColor(
                        Vec4(
                            1.0, random.uniform(0.6, 1.0), 
                            0, random.uniform(0.3, 0.7)
                        )
                    )
                else:
                    part.setZ(part.getZ() + dt * 4.0)
                    part.setX(part.getX() + math.sin(task.time * 10) * 0.05)
                    new_alpha = max(0.0, current_alpha - dt * 1.5)
                    part.setColor(Vec4(1.0, 0.8, 0.0, new_alpha))

        # G. High Jump Kick Parabolic Motion Engine
        if self.is_jumping and self.hero:
            self.jump_time += dt * 2.0
            vertical_arc = (
                (self.jump_time * 8.0) - (4.9 * self.jump_time * self.jump_time)
            )
            self.hero.setH(self.hero.getH() + dt * 720.0)
            # Spin kick hits every golem in reach once per jump
            if not self.kick_hit_done and self.jump_time > 0.4:
                self.kick_hit_done = True
                k_pos = self.hero.getPos()
                for monster in list(self.active_monsters):
                    gap = monster["node"].getPos() - k_pos
                    gap.setZ(0)
                    if gap.length() < 5.0:
                        print("🥋 SPIN KICK HIT! Monster lost 20 HP!")
                        self.damage_monster(monster, 20.0)
            if vertical_arc >= 0.0:
                self.hero.setZ(self.base_z_pos + vertical_arc)
            else:
                self.is_jumping = False
                self.hero.setZ(self.base_z_pos)
                self.hero.setH(self.pre_jump_heading)

        return task.cont

    def setup_ui(self):
        t_header = "PANDAREN RPG HORIZON ENGINE"
        t_saiyan = "GO SUPER SAIYAN (K Key)"
        t_bolt = "SHOOT LIGHTNING BOLT (L Key)"
        t_respawn = "RESPAWN MONSTER WAVE"
        t_footer = (
            "WASD: Run Along Path Track | L Key: Blast Target | "
            "Space: Spin Kick | K Key: Super Saiyan"
        )

        c_bg = (0.02, 0.02, 0.05, 0.9)
        c_font = (0.9, 0.7, 0.1, 1)
        c_clear = (0, 0, 0, 0)
        c_white = (1, 1, 1, 1)

        DirectLabel(
            text=t_header, scale=0.042, pos=(0, 0, 0.85), 
            frameColor=c_bg, text_fg=c_font
        )
        DirectButton(
            text=t_saiyan, scale=0.040, pos=(-0.95, 0, 0.15), 
            command=self.toggle_super_saiyan, 
            frameColor=(0.7, 0.5, 0.0, 0.95), text_fg=c_white
        )
        DirectButton(
            text=t_bolt, scale=0.040, pos=(-0.95, 0, 0.0), 
            command=self.shoot_lightning_bolt, 
            frameColor=(0.1, 0.5, 0.7, 0.95), text_fg=c_white
        )
        DirectButton(
            text=t_respawn, scale=0.040, pos=(-0.95, 0, -0.15), 
            command=self.spawn_monster_wave, 
            frameColor=(0.4, 0.1, 0.5, 0.95), text_fg=c_white
        )
        DirectLabel(
            text=t_footer, scale=0.035, pos=(0, 0, -0.85), 
            frameColor=c_clear, text_fg=(0.8, 0.8, 0.8, 1)
        )

        # ==========================================================
        # WOW-STYLE HUD VITALITY SYSTEMS (Experience & Leveling Bars)
        # ==========================================================
        self.ui_p_bar = DirectLabel(
            text="LVL 1 PANDA: 100% HP", scale=0.038, pos=(-0.95, 0, 0.72),
            frameColor=(0.1, 0.7, 0.2, 0.85), text_fg=c_white, text_align=0, 
            frameSize=(0, 12, -0.5, 0.8)
        )
        
        self.ui_e_bar = DirectLabel(
            text="SWARM REMAINING: 4", scale=0.038, pos=(0.4, 0, 0.72),
            frameColor=(0.1, 0.1, 0.15, 0.85), text_fg=c_white, text_align=0, 
            frameSize=(0, 15, -0.5, 0.8)
        )

        self.ui_xp_bar = DirectLabel(
            text="XP ENGINE BAR: 0 / 100", scale=0.032, pos=(-0.45, 0, -0.72),
            frameColor=(0.4, 0.1, 0.7, 0.85), text_fg=c_white, text_align=0, 
            frameSize=(0, 24, -0.3, 0.4)
        )

        self.ui_level_flash = DirectLabel(
            text="👑 LEVEL UP! POWER INCREASED! 👑", scale=0.065, pos=(0, 0, 0.3),
            frameColor=c_clear, text_fg=(1, 0.8, 0, 1)
        )
        self.ui_level_flash.hide() 

# Global boot configurations (Ensure class names match exactly)
if __name__ == "__main__":
    app = PandarenRPGAdventure()
    app.run()
