# class Test:
#     def __init__(self,data):
#         self.data = data
#
#     def next(self):
#         if self.data < 10:
#             self.data += 1
#             return self.data
#         else:
#             raise StopIteration
#
#     def __iter__(self):
#         return self
#
#
# if __name__ == '__main__':
#
#
#     a = Test(0)
#     c = tuple(a)
#     print c
#     for i in a:
#         print i
#     b = tuple(a)
#     print b

# a = [1,2]
# b = a
# print a
# print id(a)
#
# a += [3,4]
# print a
# print b
# print id(a)
# print id(b)