import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

JSON = Union[Dict[str, Any], List[Any]]


class json_migr_util:
    """
    0-based paths (standard coding):
      - objects: a.b.c
      - arrays:  a.b[0]
    Rules:
      - move:   {"action":"move","from":"a.b","to":"x.y"}
      - change: {"action":"change","path":"a.b[0]","value":"new"}
    """

    def __init__(self, *, strict: bool = False) -> None:
        self.strict = strict
        self.doc: JSON | None = None

    def migrate_json(self, mapping_json_path: str, input_json_path: str, output_json_path: str) -> None:
        mapping = self._read_json(mapping_json_path)
        self.doc = self._read_json(input_json_path)

        for rule in mapping.get("rules", []):
            action = rule.get("action")
            if action == "move":
                self.move(rule["from"], rule["to"])
            elif action == "change":
                self.change(rule["path"], rule.get("value"))
            else:
                raise ValueError(f"Unsupported action: {action}")

        self.clean_up()

        Path(output_json_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(self.doc, f, indent=2, ensure_ascii=False)

    def move(self, src_path: str, dest_path: str) -> None:
        ok, val = self._get(src_path)
        if not ok:
            if self.strict:
                raise KeyError(f"Missing source path: {src_path}")
            return
        self._set(dest_path, val)
        self._delete(src_path)

    def change(self, trgt_path: str, trgt_val: Any) -> None:
        self._set(trgt_path, trgt_val)

    def clean_up(self) -> None:
        self.doc = self._prune(self.doc)

    # --------- internals ---------

    def _read_json(self, path: str) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _parse(self, path: str) -> List[Tuple[str, str | int]]:
        # "a.b[0].c" -> [("k","a"),("k","b"),("i",0),("k","c")]
        out: List[Tuple[str, str | int]] = []
        for seg in path.split("."):
            while "[" in seg:
                key, rest = seg.split("[", 1)
                if key:
                    out.append(("k", key))
                idx_str, seg = rest.split("]", 1)
                out.append(("i", int(idx_str)))
            if seg:
                out.append(("k", seg))
        return out

    def _get(self, path: str) -> tuple[bool, Any]:
        cur: Any = self.doc
        for t, v in self._parse(path):
            if t == "k":
                if not isinstance(cur, dict) or v not in cur:
                    return False, None
                cur = cur[v]
            else:
                if not isinstance(cur, list) or v >= len(cur):
                    return False, None
                cur = cur[v]
        return True, cur

    def _set(self, path: str, value: Any) -> None:
        if self.doc is None:
            raise RuntimeError("No JSON loaded. Call migrate_json() first.")

        tokens = self._parse(path)
        cur: Any = self.doc

        for (t, v), nxt in zip(tokens[:-1], tokens[1:]):
            want_list = (nxt[0] == "i")

            if t == "k":
                if not isinstance(cur, dict):
                    raise TypeError(f"Expected object at '{v}' in '{path}'")
                cur.setdefault(v, [] if want_list else {})
                cur = cur[v]
            else:  # index
                if not isinstance(cur, list):
                    raise TypeError(f"Expected list at '[{v}]' in '{path}'")
                if v >= len(cur):
                    cur.extend([None] * (v - len(cur) + 1))
                if cur[v] is None:
                    cur[v] = [] if want_list else {}
                cur = cur[v]

        lt, lv = tokens[-1]
        if lt == "k":
            if not isinstance(cur, dict):
                raise TypeError(f"Expected object as parent of '{path}'")
            cur[lv] = value
        else:
            if not isinstance(cur, list):
                raise TypeError(f"Expected list as parent of '{path}'")
            if lv >= len(cur):
                cur.extend([None] * (lv - len(cur) + 1))
            cur[lv] = value

    def _delete(self, path: str) -> None:
        if self.doc is None:
            return

        tokens = self._parse(path)
        cur: Any = self.doc

        for t, v in tokens[:-1]:
            if t == "k":
                if not isinstance(cur, dict) or v not in cur:
                    if self.strict:
                        raise KeyError(f"Missing segment '{v}' while deleting '{path}'")
                    return
                cur = cur[v]
            else:
                if not isinstance(cur, list) or v >= len(cur):
                    if self.strict:
                        raise KeyError(f"Missing index [{v}] while deleting '{path}'")
                    return
                cur = cur[v]

        lt, lv = tokens[-1]
        if lt == "k" and isinstance(cur, dict):
            cur.pop(lv, None)
        elif lt == "i" and isinstance(cur, list) and 0 <= lv < len(cur):
            cur[lv] = None  # keep positions; cleanup trims trailing Nones

    def _prune(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            for k in list(obj.keys()):
                obj[k] = self._prune(obj[k])
                if obj[k] is None or obj[k] == {} or obj[k] == []:
                    del obj[k]
            return obj

        if isinstance(obj, list):
            for i in range(len(obj)):
                obj[i] = self._prune(obj[i])
            while obj and (obj[-1] is None or obj[-1] == {} or obj[-1] == []):
                obj.pop()
            return obj

        return obj

