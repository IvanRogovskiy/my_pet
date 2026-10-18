# AD07 — тема 06/2

C1: page(rows, cursor, limit) получает list[(timestamp:int,id:int)], пары уникальны. Вернуть первые limit пар строго после cursor в лексикографическом порядке (timestamp,id). cursor=None начинает с начала; limit — положительное целое; rows не менять.
