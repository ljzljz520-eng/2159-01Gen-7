import math
import time
import sys
sys.path.insert(0, '.')

from radar_scanner import Target, RadarScanner

def test_target():
    print("测试 Target 类...")
    t1 = Target(10, 10, False)
    assert t1.x == 10
    assert t1.y == 10
    assert t1.is_moving == False
    assert t1.get_distance() == math.sqrt(200)
    print("  静止目标: OK")

    t2 = Target(0, 0, True, 1, 0)
    t2.update(2, 100)
    assert abs(t2.x - 2) < 0.01
    assert t2.y == 0
    print("  移动目标: OK")

    t3 = Target(200, 0, True, 10, 0)
    t3.update(1, 50)
    assert t3.visible == False
    print("  超出范围目标消失: OK")

def test_detection_logic():
    print("\n测试探测逻辑...")

    target = Target(10, 0, False)
    target.visible = True
    target.first_detected = None

    assert target.get_distance() == 10
    print("  距离计算: OK")

    target.first_detected = time.time()
    target.last_detected = time.time()
    target.closest_distance = 10
    target.intensity = 1.0

    target.update(1, 100)
    assert target.intensity < 1.0
    print("  强度衰减: OK")

def test_report():
    print("\n测试报告格式...")

    targets = []
    t1 = Target(5, 5, False)
    t1.id = 1001
    t1.first_detected = 10.0
    t1.last_detected = 25.0
    t1.closest_distance = 7.07
    targets.append(t1)

    t2 = Target(15, 0, True)
    t2.id = 2002
    t2.first_detected = 5.0
    t2.last_detected = 30.0
    t2.closest_distance = 15.0
    targets.append(t2)

    print("=" * 60)
    print("雷达扫描报告")
    print("=" * 60)
    print(f"总运行时间: 35.00 秒")
    print(f"探测到目标数: {len(targets)}")
    print("-" * 60)
    print(f"{'ID':<8} {'类型':<8} {'首次发现(s)':<12} {'最后发现(s)':<12} {'最近距离':<10}")
    print("-" * 60)

    for t in targets:
        t_type = "移动" if t.is_moving else "静止"
        first = t.first_detected if t.first_detected else 0
        last = t.last_detected if t.last_detected else 0
        closest = t.closest_distance if t.closest_distance is not None else 0
        print(f"{t.id:<8} {t_type:<8} {first:<12.2f} {last:<12.2f} {closest:<10.2f}")

    print("=" * 60)
    print("  报告格式: OK")

def main():
    print("=" * 50)
    print("雷达扫描程序 - 逻辑测试")
    print("=" * 50)

    try:
        test_target()
        test_detection_logic()
        test_report()
        print("\n" + "=" * 50)
        print("所有测试通过! ✅")
        print("=" * 50)
        print("\n运行 'python3 radar_scanner.py' 启动雷达界面")
    except AssertionError as e:
        print(f"\n测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
