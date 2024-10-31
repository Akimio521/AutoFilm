import abc


class Singleton(abc.ABCMeta, type):
    """
    单例模式
    """

    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        key = cls
        if key not in cls._instances:
            cls._instances[key] = super().__call__(*args, **kwargs)
        return cls._instances[key]


if __name__ == "__main__":
    # 示例单例类
    class MySingleton1(metaclass=Singleton):
        def __init__(self, value):
            self.value = value

    class MySingleton2(metaclass=Singleton):
        def __init__(self, value):
            self.value = value

    # 测试单例
    instance1 = MySingleton1(10)
    instance2 = MySingleton1(20)
    intance3 = MySingleton2(10)

    print(instance1 is instance2)  # 输出: True
    print(instance1 is intance3)  # 输出: False
    print(instance1.value)  # 输出: 10
    print(instance2.value)  # 输出: 10
    print(intance3.value)  # 输出: 10
