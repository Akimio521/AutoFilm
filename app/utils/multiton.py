import abc


class Multiton(abc.ABCMeta, type):
    """
    多例模式
    """

    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        key = (cls, args, frozenset(kwargs.items()))
        if key not in cls._instances:
            cls._instances[key] = super().__call__(*args, **kwargs)
        return cls._instances[key]


if __name__ == "__main__":
    # 示例多例类
    class MyMultiton1(metaclass=Multiton):
        def __init__(self, value):
            self.value = value

    class MyMultiton2(metaclass=Multiton):
        def __init__(self, value):
            self.value = value

    # 测试多例
    instance1 = MyMultiton1(10)
    instance2 = MyMultiton1(20)
    instance3 = MyMultiton1(10)
    instance4 = MyMultiton2(10)

    print(instance1 is instance2)  # 输出: False
    print(instance1 is instance3)  # 输出: True
    print(instance1 is instance4)  # 输出: False
    print(instance1.value)  # 输出: 10
    print(instance2.value)  # 输出: 20
    print(instance3.value)  # 输出: 10
    print(instance4.value)  # 输出: 10
