import curses
import math
import time
import random
import threading
from collections import deque


class Target:
    def __init__(self, x, y, is_moving=False, vx=0, vy=0):
        self.x = x
        self.y = y
        self.is_moving = is_moving
        self.vx = vx
        self.vy = vy
        self.intensity = 0.0
        self.first_detected = None
        self.last_detected = None
        self.closest_distance = None
        self.visible = False
        self.id = random.randint(1000, 9999)

    def update(self, delta_time, radar_radius):
        if self.is_moving:
            self.x += self.vx * delta_time
            self.y += self.vy * delta_time
            dist = math.sqrt(self.x ** 2 + self.y ** 2)
            if dist > radar_radius * 1.5:
                self.visible = False

        if self.intensity > 0:
            self.intensity -= delta_time * 0.3
            if self.intensity < 0:
                self.intensity = 0

    def get_distance(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)


class RadarScanner:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.center_y = self.height // 2
        self.center_x = self.width // 2
        self.radar_radius = min(self.center_y, self.center_x) - 3

        self.scan_angle = 0.0
        self.scan_speed = 2.0
        self.targets = []
        self.history_blips = deque(maxlen=200)
        self.detected_targets = []
        self.running = True
        self.auto_spawn = True
        self.start_time = time.time()

        curses.curs_set(0)
        stdscr.nodelay(1)
        stdscr.timeout(50)

        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)

    def draw_radar_circle(self):
        for angle in range(0, 360, 5):
            rad = math.radians(angle)
            x = int(self.center_x + self.radar_radius * math.cos(rad))
            y = int(self.center_y + self.radar_radius * math.sin(rad))
            if 0 <= y < self.height - 1 and 0 <= x < self.width - 1:
                try:
                    self.stdscr.addch(y, x, '.', curses.color_pair(1))
                except curses.error:
                    pass

        for r in [self.radar_radius // 4, self.radar_radius // 2,
                  self.radar_radius * 3 // 4, self.radar_radius]:
            for angle in range(0, 360, 3):
                rad = math.radians(angle)
                x = int(self.center_x + r * math.cos(rad))
                y = int(self.center_y + r * math.sin(rad))
                if 0 <= y < self.height - 1 and 0 <= x < self.width - 1:
                    try:
                        self.stdscr.addch(y, x, '.', curses.color_pair(1))
                    except curses.error:
                        pass

        for angle in [0, 90, 180, 270]:
            rad = math.radians(angle)
            for r in range(0, self.radar_radius, 2):
                x = int(self.center_x + r * math.cos(rad))
                y = int(self.center_y + r * math.sin(rad))
                if 0 <= y < self.height - 1 and 0 <= x < self.width - 1:
                    try:
                        self.stdscr.addch(y, x, '.', curses.color_pair(1))
                    except curses.error:
                        pass

    def draw_scan_line(self):
        for r in range(0, self.radar_radius):
            x = int(self.center_x + r * math.cos(self.scan_angle))
            y = int(self.center_y + r * math.sin(self.scan_angle))
            if 0 <= y < self.height - 1 and 0 <= x < self.width - 1:
                try:
                    intensity = 1.0 - (r / self.radar_radius) * 0.5
                    if intensity > 0.7:
                        self.stdscr.addch(y, x, '#', curses.color_pair(1))
                    else:
                        self.stdscr.addch(y, x, '=', curses.color_pair(1))
                except curses.error:
                    pass

    def draw_history_blips(self):
        current_time = time.time()
        new_blips = []
        for blip in self.history_blips:
            x, y, intensity, spawn_time = blip
            age = current_time - spawn_time
            fade = max(0, 1.0 - age / 3.0)
            if fade > 0:
                new_blips.append(blip)
                screen_x = int(self.center_x + x)
                screen_y = int(self.center_y + y)
                if 0 <= screen_y < self.height - 1 and 0 <= screen_x < self.width - 1:
                    try:
                        if fade > 0.7:
                            char = 'O'
                            color = curses.color_pair(3)
                        elif fade > 0.4:
                            char = 'o'
                            color = curses.color_pair(2)
                        else:
                            char = '.'
                            color = curses.color_pair(1)
                        self.stdscr.addch(screen_y, screen_x, char, color)
                    except curses.error:
                        pass
        self.history_blips = deque(new_blips, maxlen=200)

    def draw_targets(self):
        for target in self.targets:
            if not target.visible:
                continue
            screen_x = int(self.center_x + target.x)
            screen_y = int(self.center_y + target.y)
            if 0 <= screen_y < self.height - 1 and 0 <= screen_x < self.width - 1:
                try:
                    if target.intensity > 0.7:
                        char = 'O'
                        color = curses.color_pair(3)
                    elif target.intensity > 0.4:
                        char = 'o'
                        color = curses.color_pair(2)
                    else:
                        char = '.'
                        color = curses.color_pair(1)
                    self.stdscr.addch(screen_y, screen_x, char, color)
                except curses.error:
                    pass

    def detect_targets(self):
        current_time = time.time()
        scan_tolerance = 0.15

        for target in self.targets:
            if not target.visible:
                continue

            target_angle = math.atan2(target.y, target.x)
            if target_angle < 0:
                target_angle += 2 * math.pi

            scan_ang = self.scan_angle % (2 * math.pi)
            if scan_ang < 0:
                scan_ang += 2 * math.pi

            angle_diff = abs(scan_ang - target_angle)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff

            if angle_diff < scan_tolerance:
                dist = target.get_distance()
                if dist <= self.radar_radius:
                    self.history_blips.append((target.x, target.y, 1.0, current_time))

                    if target.first_detected is None:
                        target.first_detected = current_time
                        target.closest_distance = dist
                        self.detected_targets.append(target)
                    else:
                        if target.closest_distance is None or dist < target.closest_distance:
                            target.closest_distance = dist
                    target.last_detected = current_time
                    target.intensity = 1.0

    def update_targets(self, delta_time):
        for target in self.targets:
            target.update(delta_time, self.radar_radius)

    def spawn_random_target(self):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(self.radar_radius * 0.2, self.radar_radius * 0.9)
        x = dist * math.cos(angle)
        y = dist * math.sin(angle)

        is_moving = random.choice([True, False])
        if is_moving:
            speed = random.uniform(2, 8)
            move_angle = angle + math.pi + random.uniform(-0.5, 0.5)
            vx = speed * math.cos(move_angle)
            vy = speed * math.sin(move_angle)
        else:
            vx = 0
            vy = 0

        target = Target(x, y, is_moving, vx, vy)
        target.visible = True
        self.targets.append(target)

    def add_static_target(self, x, y):
        target = Target(x, y, False, 0, 0)
        target.visible = True
        self.targets.append(target)
        return target

    def add_moving_target(self, x, y, vx, vy):
        target = Target(x, y, True, vx, vy)
        target.visible = True
        self.targets.append(target)
        return target

    def draw_ui(self):
        elapsed = time.time() - self.start_time
        angle_deg = math.degrees(self.scan_angle) % 360

        info_lines = [
            "=== 雷达扫描系统 ===",
            f"扫描角度: {angle_deg:6.1f}°",
            f"扫描速度: {self.scan_speed:.1f} rad/s",
            f"运行时间: {elapsed:6.1f} s",
            f"目标总数: {len([t for t in self.targets if t.visible])}",
            f"已探测: {len(self.detected_targets)}",
            "",
            "控制:",
            "  ↑/↓ - 调整速度",
            "  a     - 添加静止目标",
            "  m     - 添加移动目标",
            "  s     - 切换自动生成",
            "  q     - 退出",
        ]

        for i, line in enumerate(info_lines):
            y = 2 + i
            if y < self.height - 1:
                try:
                    self.stdscr.addstr(y, 2, line, curses.color_pair(4))
                except curses.error:
                    pass

        status = "自动生成: 开" if self.auto_spawn else "自动生成: 关"
        try:
            self.stdscr.addstr(self.height - 2, 2, status, curses.color_pair(5))
        except curses.error:
            pass

        try:
            self.stdscr.addstr(self.height - 1, 2, "按 'q' 退出程序", curses.color_pair(5))
        except curses.error:
            pass

    def handle_input(self):
        key = self.stdscr.getch()
        if key == ord('q'):
            self.running = False
        elif key == curses.KEY_UP:
            self.scan_speed = min(8.0, self.scan_speed + 0.5)
        elif key == curses.KEY_DOWN:
            self.scan_speed = max(0.5, self.scan_speed - 0.5)
        elif key == ord('a'):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(self.radar_radius * 0.3, self.radar_radius * 0.8)
            x = dist * math.cos(angle)
            y = dist * math.sin(angle)
            self.add_static_target(x, y)
        elif key == ord('m'):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(self.radar_radius * 0.3, self.radar_radius * 0.8)
            x = dist * math.cos(angle)
            y = dist * math.sin(angle)
            speed = random.uniform(3, 10)
            move_angle = angle + math.pi + random.uniform(-0.3, 0.3)
            vx = speed * math.cos(move_angle)
            vy = speed * math.sin(move_angle)
            self.add_moving_target(x, y, vx, vy)
        elif key == ord('s'):
            self.auto_spawn = not self.auto_spawn

    def print_report(self):
        print("\n" + "=" * 60)
        print("雷达扫描报告")
        print("=" * 60)
        print(f"总运行时间: {time.time() - self.start_time:.2f} 秒")
        print(f"探测到目标数: {len(self.detected_targets)}")
        print("-" * 60)
        print(f"{'ID':<8} {'类型':<8} {'首次发现(s)':<12} {'最后发现(s)':<12} {'最近距离':<10}")
        print("-" * 60)

        for target in self.detected_targets:
            target_type = "移动" if target.is_moving else "静止"
            first = (target.first_detected - self.start_time) if target.first_detected else 0
            last = (target.last_detected - self.start_time) if target.last_detected else 0
            closest = target.closest_distance if target.closest_distance is not None else 0
            print(f"{target.id:<8} {target_type:<8} {first:<12.2f} {last:<12.2f} {closest:<10.2f}")

        print("=" * 60)

    def run(self):
        last_time = time.time()
        spawn_timer = 0

        while self.running:
            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time

            self.scan_angle += self.scan_speed * delta_time
            if self.scan_angle > 2 * math.pi:
                self.scan_angle -= 2 * math.pi

            if self.auto_spawn:
                spawn_timer += delta_time
                if spawn_timer > 2.0 and len([t for t in self.targets if t.visible]) < 8:
                    self.spawn_random_target()
                    spawn_timer = 0

            self.update_targets(delta_time)
            self.detect_targets()

            self.stdscr.erase()
            self.draw_radar_circle()
            self.draw_history_blips()
            self.draw_scan_line()
            self.draw_targets()
            self.draw_ui()
            self.stdscr.refresh()

            self.handle_input()

        self.print_report()


def main():
    print("欢迎使用命令行雷达扫描系统")
    print("程序将在终端中启动雷达界面...")
    print("请确保终端窗口足够大 (建议至少 80x30)")
    print("按 Enter 继续，或按 Ctrl+C 退出...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n程序已取消")
        return

    try:
        curses.wrapper(lambda stdscr: RadarScanner(stdscr).run())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        print("请确保终端支持 curses 且窗口大小足够")


if __name__ == "__main__":
    main()
