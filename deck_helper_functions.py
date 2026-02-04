from aqt import mw
from aqt.qt import *

import time


def get_root_deck_id(deck_id):
    deck = mw.col.decks.get(deck_id)
    while "::" in deck["name"]:
        parent_name = deck["name"].rsplit("::", 1)[0]
        deck = mw.col.decks.by_name(parent_name)
    return deck["id"]

def deck_tree_is_done(root_deck_id: int) -> bool:
    root = mw.col.sched.deck_due_tree()

    def walk(node):
        if node.deck_id == root_deck_id:
            return subtree_is_done(node)
        for child in node.children:
            result = walk(child)
            if result is not None:
                return result
        return None

    def subtree_is_done(node):
        if node.new_count + node.learn_count + node.review_count > 0:
            return False
        return all(subtree_is_done(child) for child in node.children)

    result = walk(root)
    return bool(result)


