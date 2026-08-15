"hirosaki": {
        "name": "弘前市",
        "pdf": "hirosaki.pdf",
        "pdf_w": 595.2,
        "pdf_h": 841.68,
        "fields": {
            "address":  (172, 106, 9),
            "furigana": (130, 130, 9),
            # 氏名は「手書きしてください」という注記があるため自動入力しない
        },
        "dob_fields": {
            "year":  (289, 159, 9),
            "month": (311, 159, 9),
            "day":   (334, 159, 9),
        },
        "circles": {
            "pref": {},  # 都道府県欄なし
            "era": {
                "大": (293.21, 141.0),
                "昭": (308.09, 141.0),
                "平": (322.97, 141.0),
                "西": (337.85, 141.0),  # 西暦を選ぶ場合の丸（令和欄は無いため）
            },
            "radius_x": 5.5,
            "radius_y": 5.5,
        },
        "has_prefecture_field": False,
        "tel_split": True,
        "seireki_char": "西",  # 令和生まれの場合は西暦で記入
        "tel_fields": {
            "part1": (420, 130, 9),
            "part2": (484, 130, 9),
            "part3": (531, 130, 9),
        },
    },
