// KoshPack unified sharpening / modification bench v0.4.
//
// This is the first executable vertical slice for the FINAL shared system:
// - one physical forge bench;
// - persistent 2-3 modification slots stored in minecraft:custom_data;
// - sequential I -> II -> III -> IV upgrades;
// - free removal without material refund;
// - armor, weapons and tools share the same data model.
//
// Catalog v0.4: all 24 approved armor treatments plus the shared weapon,
// ranged and tool treatment families are selectable through one bench.

var KOSH_FORGE_SESSIONS = {}

var KOSH_FORGE_DATA_COMPONENTS = Java.loadClass('net.minecraft.core.component.DataComponents')
var KOSH_FORGE_ITEM_LORE = Java.loadClass('net.minecraft.world.item.component.ItemLore')
var KOSH_FORGE_ARRAY_LIST = Java.loadClass('java.util.ArrayList')

var KOSH_ARMOR_NAMESPACES = {
  koshpackminerhelmet: true,
  koshpackengineerhelmet: true,
  koshpackscouthelmet: true,
  koshpackbuilderhelmet: true,
  koshpackmedichelmet: true,
  koshpackfarmerhelmet: true,
  koshpackblacksmithhelmet: true,
  koshpackfisherhelmet: true,
  koshpacklumberjackhelmet: true,
  koshpackdiverhelmet: true,
  koshpackfighterarmor: true,
  koshpackarcherarmor: true,
  koshpackshooterarmor: true,
  koshpackartilleryarmor: true,
  koshpackhunterarmor: true,
  koshpackresearcherarmor: true,
  koshpackpilothelmet: true
}

var KOSH_FORGE_MODS = {
  "reinforcement": {
    "name": "Укреплённая броня",
    "category": "armor",
    "icon": "minecraft:iron_chestplate",
    "max": 4,
    "description": "Снижает подходящий входящий урон.",
    "pieces": [
      "all"
    ],
    "effectText": [
      "",
      "−2% подходящего входящего урона",
      "−3% подходящего входящего урона",
      "−4% подходящего входящего урона",
      "−5% подходящего входящего урона"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 4,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 2,
        "label": "Кожа"
      }
    ]
  },
  "thermal": {
    "name": "Термостойкая обработка",
    "category": "armor",
    "icon": "minecraft:magma_cream",
    "max": 4,
    "description": "Снижает урон от огня и лавы.",
    "pieces": [
      "all"
    ],
    "effectText": [
      "",
      "−4% огня/лавы",
      "−6% огня/лавы",
      "−8% огня/лавы",
      "−10% огня/лавы"
    ],
    "base": [
      {
        "ingredient": "minecraft:brick",
        "count": 4,
        "label": "Кирпич"
      },
      {
        "ingredient": "minecraft:clay_ball",
        "count": 2,
        "label": "Глина"
      }
    ]
  },
  "blast": {
    "name": "Противовзрывной подбой",
    "category": "armor",
    "icon": "minecraft:tnt",
    "max": 4,
    "description": "Снижает взрывной урон.",
    "pieces": [
      "all"
    ],
    "effectText": [
      "",
      "−4% взрывного урона",
      "−6% взрывного урона",
      "−8% взрывного урона",
      "−10% взрывного урона"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:white_wool",
        "count": 4,
        "label": "Белая шерсть"
      }
    ]
  },
  "ballistic": {
    "name": "Баллистическое усиление",
    "category": "armor",
    "icon": "minecraft:arrow",
    "max": 4,
    "description": "Снижает урон снарядами.",
    "pieces": [
      "all"
    ],
    "effectText": [
      "",
      "−4% урона снарядами",
      "−6% урона снарядами",
      "−8% урона снарядами",
      "−10% урона снарядами"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 4,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:chain",
        "count": 2,
        "label": "Цепь"
      }
    ]
  },
  "hardening": {
    "name": "Закалка",
    "category": "armor",
    "icon": "minecraft:anvil",
    "max": 4,
    "description": "Снижает обычный износ детали.",
    "pieces": [
      "all"
    ],
    "effectText": [
      "",
      "−10% обычного износа",
      "−20% обычного износа",
      "−30% обычного износа",
      "−40% обычного износа"
    ],
    "base": [
      {
        "ingredient": "minecraft:coal",
        "count": 4,
        "label": "Уголь"
      },
      {
        "ingredient": "minecraft:flint",
        "count": 2,
        "label": "Кремень"
      }
    ]
  },
  "thorns": {
    "name": "Шипованная поверхность",
    "category": "armor",
    "icon": "minecraft:iron_nugget",
    "max": 4,
    "description": "Может ранить атакующего в ближнем бою.",
    "pieces": [
      "all"
    ],
    "effectText": [
      "",
      "10% шанс • 1 урон",
      "15% шанс • 1 урон",
      "20% шанс • 2 урона",
      "25% шанс • 2 урона"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 4,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:flint",
        "count": 4,
        "label": "Кремень"
      }
    ]
  },
  "breathing": {
    "name": "Дыхательный резерв",
    "category": "armor",
    "icon": "minecraft:glass_bottle",
    "max": 4,
    "description": "Даёт дополнительный запас воздуха под водой.",
    "pieces": [
      "helmet"
    ],
    "effectText": [
      "",
      "+15 сек воздуха",
      "+30 сек воздуха",
      "+45 сек воздуха",
      "+60 сек воздуха"
    ],
    "base": [
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 4,
        "label": "Медный слиток"
      },
      {
        "ingredient": "minecraft:glass",
        "count": 2,
        "label": "Стекло"
      }
    ]
  },
  "aqua_work": {
    "name": "Подводная адаптация",
    "category": "armor",
    "icon": "minecraft:prismarine_shard",
    "max": 4,
    "description": "Уменьшает штраф добычи под водой.",
    "pieces": [
      "helmet"
    ],
    "effectText": [
      "",
      "−25% штрафа добычи под водой",
      "−50% штрафа добычи под водой",
      "−75% штрафа добычи под водой",
      "Штраф погружения снят"
    ],
    "base": [
      {
        "ingredient": "minecraft:prismarine_shard",
        "count": 4,
        "label": "Призмариновый осколок"
      },
      {
        "ingredient": "minecraft:glass",
        "count": 2,
        "label": "Стекло"
      }
    ]
  },
  "sneaking": {
    "name": "Подвижные сочленения",
    "category": "armor",
    "icon": "minecraft:leather_leggings",
    "max": 4,
    "description": "Повышает скорость движения в приседе.",
    "pieces": [
      "leggings"
    ],
    "effectText": [
      "",
      "Присед: 45% обычной скорости",
      "Присед: 60% обычной скорости",
      "Присед: 75% обычной скорости",
      "Присед: 90% обычной скорости"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 4,
        "label": "Кожа"
      }
    ]
  },
  "cushion": {
    "name": "Амортизация",
    "category": "armor",
    "icon": "minecraft:slime_ball",
    "max": 4,
    "description": "Снижает урон от падения.",
    "pieces": [
      "boots"
    ],
    "effectText": [
      "",
      "−15% урона от падения",
      "−30% урона от падения",
      "−45% урона от падения",
      "−60% урона от падения"
    ],
    "base": [
      {
        "ingredient": "minecraft:slime_ball",
        "count": 2,
        "label": "Слизь"
      },
      {
        "ingredient": "minecraft:white_wool",
        "count": 4,
        "label": "Белая шерсть"
      }
    ]
  },
  "hydrodynamic": {
    "name": "Гидродинамика",
    "category": "armor",
    "icon": "minecraft:prismarine_crystals",
    "max": 4,
    "description": "Повышает скорость движения в воде.",
    "pieces": [
      "boots"
    ],
    "conflictGroup": "water_boots",
    "effectText": [
      "",
      "+15% скорости в воде",
      "+30% скорости в воде",
      "+45% скорости в воде",
      "+60% скорости в воде"
    ],
    "base": [
      {
        "ingredient": "minecraft:prismarine_shard",
        "count": 4,
        "label": "Призмариновый осколок"
      },
      {
        "ingredient": "minecraft:dried_kelp",
        "count": 4,
        "label": "Сушёная ламинария"
      }
    ]
  },
  "frost": {
    "name": "Морозная подошва",
    "category": "armor",
    "icon": "minecraft:packed_ice",
    "max": 4,
    "description": "Создаёт временный лёд под ногами.",
    "pieces": [
      "boots"
    ],
    "conflictGroup": "water_boots",
    "effectText": [
      "",
      "Радиус льда 2 блока",
      "Радиус льда 3 блока",
      "Радиус льда 4 блока",
      "Радиус льда 5 блоков"
    ],
    "base": [
      {
        "ingredient": "minecraft:packed_ice",
        "count": 2,
        "label": "Плотный лёд"
      },
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 2,
        "label": "Медный слиток"
      }
    ]
  },
  "soul": {
    "name": "Душеход",
    "category": "armor",
    "icon": "minecraft:soul_sand",
    "max": 4,
    "description": "Улучшает движение по песку и почве душ.",
    "pieces": [
      "boots"
    ],
    "costMode": "soul",
    "levelMinArmorTier": [
      0,
      3,
      3,
      4,
      4
    ],
    "effectText": [
      "",
      "Убирает замедление песка душ",
      "+10% на песке/почве душ",
      "+20% на песке/почве душ",
      "+30% на песке/почве душ"
    ],
    "base": [
      {
        "ingredient": "minecraft:soul_sand",
        "count": 2,
        "label": "Песок душ"
      },
      {
        "ingredient": "minecraft:soul_soil",
        "count": 2,
        "label": "Почва душ"
      }
    ]
  },
  "walking": {
    "name": "Облегчённая поступь",
    "category": "armor",
    "icon": "minecraft:feather",
    "max": 4,
    "description": "Повышает наземную скорость.",
    "pieces": [
      "boots"
    ],
    "effectText": [
      "",
      "+3% наземной скорости",
      "+6% наземной скорости",
      "+9% наземной скорости",
      "+12% наземной скорости"
    ],
    "base": [
      {
        "ingredient": "minecraft:leather",
        "count": 4,
        "label": "Кожа"
      },
      {
        "ingredient": "minecraft:feather",
        "count": 2,
        "label": "Перо"
      }
    ]
  },
  "stability": {
    "name": "Стабилизирующий каркас",
    "category": "armor",
    "icon": "minecraft:chain",
    "max": 4,
    "description": "Снижает силу отбрасывания.",
    "pieces": [
      "chestplate"
    ],
    "effectText": [
      "",
      "−10% силы отбрасывания",
      "−20% силы отбрасывания",
      "−30% силы отбрасывания",
      "−40% силы отбрасывания"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 4,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:chain",
        "count": 2,
        "label": "Цепь"
      }
    ]
  },
  "grip": {
    "name": "Цепкая подошва",
    "category": "armor",
    "icon": "minecraft:flint",
    "max": 4,
    "description": "Уменьшает дополнительное скольжение на льду.",
    "pieces": [
      "boots"
    ],
    "effectText": [
      "",
      "−25% скольжения льда",
      "−50% скольжения льда",
      "−75% скольжения льда",
      "Доп. скольжение льда снято"
    ],
    "base": [
      {
        "ingredient": "minecraft:flint",
        "count": 4,
        "label": "Кремень"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 2,
        "label": "Кожа"
      }
    ]
  },
  "step": {
    "name": "Высокий шаг",
    "category": "armor",
    "icon": "minecraft:iron_boots",
    "max": 1,
    "description": "Позволяет перешагивать уступ до 1 блока.",
    "pieces": [
      "boots"
    ],
    "minArmorTier": 2,
    "costMode": "step",
    "effectText": [
      "",
      "Шаг до 1 блока"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 2,
        "label": "Медный слиток"
      }
    ]
  },
  "spring": {
    "name": "Пружинная подошва",
    "category": "armor",
    "icon": "minecraft:rabbit_foot",
    "max": 4,
    "description": "Увеличивает высоту прыжка.",
    "pieces": [
      "boots"
    ],
    "effectText": [
      "",
      "Прыжок ≈1,5 блока",
      "Прыжок ≈2 блока",
      "Прыжок ≈2,5 блока",
      "Прыжок ≈3 блока"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 4,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:slime_ball",
        "count": 2,
        "label": "Слизь"
      }
    ]
  },
  "quiet": {
    "name": "Мягкая поступь",
    "category": "armor",
    "icon": "minecraft:white_wool",
    "max": 1,
    "description": "Обычная ходьба не должна вызывать скалк-вибрации.",
    "pieces": [
      "boots"
    ],
    "minArmorTier": 2,
    "costMode": "quiet",
    "effectText": [
      "",
      "Тихая обычная ходьба"
    ],
    "base": [
      {
        "ingredient": "minecraft:white_wool",
        "count": 4,
        "label": "Белая шерсть"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 2,
        "label": "Кожа"
      },
      {
        "ingredient": "minecraft:sculk_sensor",
        "count": 1,
        "label": "Скалк-сенсор"
      }
    ]
  },
  "kneepads": {
    "name": "Упорные наколенники",
    "category": "armor",
    "icon": "minecraft:iron_leggings",
    "max": 1,
    "description": "При приседе на земле помогают не сорваться с края от отбрасывания.",
    "pieces": [
      "leggings"
    ],
    "minArmorTier": 2,
    "costMode": "step",
    "effectText": [
      "",
      "Фиксация у края при приседе"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 4,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 2,
        "label": "Кожа"
      }
    ]
  },
  "streamline": {
    "name": "Обтекаемый каркас",
    "category": "armor",
    "icon": "minecraft:shield",
    "max": 4,
    "description": "Снижает замедление при использовании лука или щита.",
    "pieces": [
      "chestplate"
    ],
    "effectText": [
      "",
      "−15% замедления использования",
      "−30% замедления использования",
      "−45% замедления использования",
      "−60% замедления использования"
    ],
    "base": [
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 2,
        "label": "Медный слиток"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 4,
        "label": "Кожа"
      }
    ]
  },
  "harness": {
    "name": "Страховочная подвеска",
    "category": "armor",
    "icon": "minecraft:lead",
    "max": 4,
    "description": "Снижает урон столкновений при полёте.",
    "pieces": [
      "chestplate"
    ],
    "effectText": [
      "",
      "−15% collision-урона",
      "−30% collision-урона",
      "−45% collision-урона",
      "−60% collision-урона"
    ],
    "base": [
      {
        "ingredient": "minecraft:string",
        "count": 4,
        "label": "Нить"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 2,
        "label": "Кожа"
      },
      {
        "ingredient": "minecraft:slime_ball",
        "count": 2,
        "label": "Слизь"
      }
    ]
  },
  "filter": {
    "name": "Светофильтр",
    "category": "armor",
    "icon": "minecraft:tinted_glass",
    "max": 4,
    "description": "Сокращает длительность новых Слепоты и Тьмы.",
    "pieces": [
      "helmet"
    ],
    "effectText": [
      "",
      "−15% длительности Слепоты/Тьмы",
      "−30% длительности Слепоты/Тьмы",
      "−45% длительности Слепоты/Тьмы",
      "−60% длительности Слепоты/Тьмы"
    ],
    "base": [
      {
        "ingredient": "minecraft:tinted_glass",
        "count": 2,
        "label": "Тонированное стекло"
      },
      {
        "ingredient": "minecraft:amethyst_shard",
        "count": 2,
        "label": "Осколок аметиста"
      }
    ]
  },
  "lining": {
    "name": "Герметичная подкладка",
    "category": "armor",
    "icon": "minecraft:honeycomb",
    "max": 4,
    "description": "Замедляет накопление замерзания.",
    "pieces": [
      "all"
    ],
    "effectText": [
      "",
      "−10% скорости замерзания",
      "−15% скорости замерзания",
      "−20% скорости замерзания",
      "−25% скорости замерзания"
    ],
    "base": [
      {
        "ingredient": "minecraft:leather",
        "count": 2,
        "label": "Кожа"
      },
      {
        "ingredient": "minecraft:white_wool",
        "count": 2,
        "label": "Белая шерсть"
      },
      {
        "ingredient": "minecraft:honeycomb",
        "count": 2,
        "label": "Пчелиные соты"
      }
    ]
  },
  "fine_honing": {
    "name": "Тонкая заточка",
    "category": "weapon",
    "icon": "minecraft:iron_sword",
    "max": 4,
    "description": "Универсальный прирост ближнего урона.",
    "conflictGroup": "edge",
    "families": [
      "blade",
      "dagger",
      "rapier",
      "katana",
      "machete",
      "claymore",
      "twinblade",
      "spear",
      "glaive",
      "scythe",
      "axe",
      "chakram"
    ],
    "effectText": [
      "",
      "+4% ближнего урона",
      "+8% ближнего урона",
      "+12% ближнего урона",
      "+16% ближнего урона"
    ],
    "base": [
      {
        "ingredient": "minecraft:quartz",
        "count": 2,
        "label": "Кварц"
      },
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 1,
        "label": "Железный слиток"
      }
    ]
  },
  "silvered_edge": {
    "name": "Серебрение кромки/бойка",
    "category": "weapon",
    "icon": "minecraft:gold_nugget",
    "max": 4,
    "description": "Сильнее против нежити; почти без общего бонуса.",
    "conflictGroup": "edge",
    "families": [
      "blade",
      "dagger",
      "rapier",
      "katana",
      "machete",
      "claymore",
      "twinblade",
      "spear",
      "glaive",
      "scythe",
      "axe",
      "hammer"
    ],
    "effectText": [
      "",
      "+8% урона нежити",
      "+16% урона нежити",
      "+24% урона нежити",
      "+32% урона нежити"
    ],
    "base": [
      {
        "ingredient": "minecraft:gold_ingot",
        "count": 2,
        "label": "Плакирующий металл"
      },
      {
        "ingredient": "minecraft:amethyst_shard",
        "count": 1,
        "label": "Осколок аметиста"
      }
    ]
  },
  "serrated_edge": {
    "name": "Зубчатая кромка / шипованный наконечник",
    "category": "weapon",
    "icon": "minecraft:flint",
    "max": 4,
    "description": "Специализация против членистоногих и контроль.",
    "conflictGroup": "edge",
    "families": [
      "blade",
      "dagger",
      "rapier",
      "katana",
      "machete",
      "claymore",
      "twinblade",
      "spear",
      "glaive",
      "scythe",
      "axe",
      "chakram"
    ],
    "effectText": [
      "",
      "+6% против членистоногих",
      "+12% против членистоногих",
      "+18% против членистоногих",
      "+24% против членистоногих"
    ],
    "base": [
      {
        "ingredient": "minecraft:flint",
        "count": 4,
        "label": "Кремень"
      },
      {
        "ingredient": "minecraft:iron_nugget",
        "count": 4,
        "label": "Железный самородок"
      }
    ]
  },
  "harvest_edge": {
    "name": "Разделочная кромка",
    "category": "weapon",
    "icon": "minecraft:golden_sword",
    "max": 4,
    "description": "Повышает добычу с существ ценой боевой специализации.",
    "conflictGroup": "edge",
    "families": [
      "blade",
      "dagger",
      "machete",
      "scythe",
      "axe"
    ],
    "effectText": [
      "",
      "+5% шанс доп. добычи",
      "+10% шанс доп. добычи",
      "+15% шанс доп. добычи",
      "+20% шанс доп. добычи"
    ],
    "base": [
      {
        "ingredient": "minecraft:gold_ingot",
        "count": 2,
        "label": "Золото"
      },
      {
        "ingredient": "minecraft:amethyst_shard",
        "count": 2,
        "label": "Осколок аметиста"
      }
    ]
  },
  "reinforced_frame": {
    "name": "Усиленный каркас / хвостовик",
    "category": "weapon",
    "icon": "minecraft:iron_ingot",
    "max": 4,
    "description": "Снижает обычный износ оружия.",
    "families": [
      "all",
      "unique"
    ],
    "effectText": [
      "",
      "−15% обычного износа",
      "−25% обычного износа",
      "−35% обычного износа",
      "−45% обычного износа"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 3,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:chain",
        "count": 1,
        "label": "Цепь"
      }
    ]
  },
  "weighted_pommel": {
    "name": "Противовес / ударная масса",
    "category": "weapon",
    "icon": "minecraft:anvil",
    "max": 4,
    "description": "Усиливает отбрасывание ценой скорости.",
    "families": [
      "blade",
      "machete",
      "claymore",
      "spear",
      "glaive",
      "axe",
      "hammer"
    ],
    "effectText": [
      "",
      "+10% отбрасывания",
      "+20% отбрасывания",
      "+30% отбрасывания",
      "+40% отбрасывания"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 4,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 2,
        "label": "Медный слиток"
      }
    ]
  },
  "wide_sweep": {
    "name": "Широкая геометрия удара",
    "category": "weapon",
    "icon": "minecraft:iron_sword",
    "max": 4,
    "description": "Усиливает размашистые атаки.",
    "families": [
      "blade",
      "machete",
      "claymore",
      "twinblade",
      "glaive",
      "scythe"
    ],
    "effectText": [
      "",
      "+8% урона по соседним целям",
      "+12% урона по соседним целям",
      "+16% урона по соседним целям",
      "+20% урона по соседним целям"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:quartz",
        "count": 2,
        "label": "Кварц"
      }
    ]
  },
  "penetrating_bevel": {
    "name": "Пробивная геометрия",
    "category": "weapon",
    "icon": "minecraft:diamond",
    "max": 4,
    "description": "Повышает эффективность против бронированных целей.",
    "families": [
      "blade",
      "dagger",
      "rapier",
      "katana",
      "spear",
      "glaive",
      "axe",
      "hammer"
    ],
    "effectText": [
      "",
      "+5% против бронированных",
      "+10% против бронированных",
      "+15% против бронированных",
      "+20% против бронированных"
    ],
    "base": [
      {
        "ingredient": "minecraft:obsidian",
        "count": 2,
        "label": "Обсидиан"
      },
      {
        "ingredient": "minecraft:diamond",
        "count": 1,
        "label": "Алмаз"
      }
    ]
  },
  "light_grip": {
    "name": "Облегчённая рукоять / баланс",
    "category": "weapon",
    "icon": "minecraft:leather",
    "max": 4,
    "description": "Ускоряет обращение с оружием ценой импульса.",
    "families": [
      "blade",
      "dagger",
      "rapier",
      "katana",
      "machete",
      "twinblade",
      "spear",
      "glaive",
      "scythe",
      "axe",
      "chakram",
      "unique"
    ],
    "effectText": [
      "",
      "+3% скорости атаки",
      "+6% скорости атаки",
      "+9% скорости атаки",
      "+12% скорости атаки"
    ],
    "base": [
      {
        "ingredient": "minecraft:leather",
        "count": 2,
        "label": "Кожа"
      },
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 2,
        "label": "Медный слиток"
      }
    ]
  },
  "ignition_insert": {
    "name": "Огненная вставка",
    "category": "weapon",
    "icon": "minecraft:blaze_powder",
    "max": 4,
    "description": "Поджигает цель; пост-Nether обработка.",
    "families": [
      "blade",
      "katana",
      "machete",
      "claymore",
      "spear",
      "glaive",
      "scythe",
      "axe"
    ],
    "effectText": [
      "",
      "Поджог 2 сек",
      "Поджог 3 сек",
      "Поджог 4 сек",
      "Поджог 5 сек"
    ],
    "base": [
      {
        "ingredient": "minecraft:blaze_powder",
        "count": 2,
        "label": "Огненный порошок"
      },
      {
        "ingredient": "minecraft:magma_cream",
        "count": 1,
        "label": "Магмовый крем"
      }
    ]
  },
  "tempered_structure": {
    "name": "Термообработка конструкции",
    "category": "weapon",
    "icon": "minecraft:blast_furnace",
    "max": 4,
    "description": "Дополнительно снижает износ, но слабее усиленного каркаса.",
    "families": [
      "all",
      "unique"
    ],
    "effectText": [
      "",
      "−8% износа",
      "−12% износа",
      "−16% износа",
      "−20% износа"
    ],
    "base": [
      {
        "ingredient": "minecraft:coal",
        "count": 2,
        "label": "Уголь"
      },
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      }
    ]
  },
  "reinforced_limbs": {
    "name": "Усиленные плечи",
    "category": "weapon",
    "icon": "minecraft:bow",
    "max": 4,
    "description": "Повышает урон стрел ценой более тяжёлого натяжения.",
    "families": [
      "bow"
    ],
    "effectText": [
      "",
      "+5% урона снаряда",
      "+10% урона снаряда",
      "+15% урона снаряда",
      "+20% урона снаряда"
    ],
    "base": [
      {
        "ingredient": "minecraft:string",
        "count": 3,
        "label": "Нить"
      },
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      }
    ]
  },
  "fast_string": {
    "name": "Быстрая тетива",
    "category": "weapon",
    "icon": "minecraft:string",
    "max": 4,
    "description": "Ускоряет обращение с луком ценой мощности.",
    "families": [
      "bow"
    ],
    "effectText": [
      "",
      "Быстрое натяжение I",
      "Быстрое натяжение II",
      "Быстрое натяжение III",
      "Быстрое натяжение IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:string",
        "count": 4,
        "label": "Нить"
      },
      {
        "ingredient": "minecraft:rabbit_hide",
        "count": 2,
        "label": "Кроличья шкурка"
      }
    ]
  },
  "stabilized_grip": {
    "name": "Стабилизированная рукоять",
    "category": "weapon",
    "icon": "minecraft:spyglass",
    "max": 4,
    "description": "Снижает разброс дальнего оружия.",
    "families": [
      "bow",
      "crossbow",
      "slingshot"
    ],
    "effectText": [
      "",
      "Стабилизация I",
      "Стабилизация II",
      "Стабилизация III",
      "Стабилизация IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 2,
        "label": "Медный слиток"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 2,
        "label": "Кожа"
      }
    ]
  },
  "incendiary_setup": {
    "name": "Зажигательный модуль",
    "category": "weapon",
    "icon": "minecraft:fire_charge",
    "max": 4,
    "description": "Поджигает цели дальними снарядами.",
    "families": [
      "bow",
      "crossbow",
      "slingshot"
    ],
    "effectText": [
      "",
      "Поджог снарядом 2 сек",
      "Поджог снарядом 3 сек",
      "Поджог снарядом 4 сек",
      "Поджог снарядом 5 сек"
    ],
    "base": [
      {
        "ingredient": "minecraft:fire_charge",
        "count": 2,
        "label": "Огненный заряд"
      },
      {
        "ingredient": "minecraft:blaze_powder",
        "count": 1,
        "label": "Огненный порошок"
      }
    ]
  },
  "reinforced_prod": {
    "name": "Усиленная дуга арбалета",
    "category": "weapon",
    "icon": "minecraft:crossbow",
    "max": 4,
    "description": "Повышает урон арбалета.",
    "families": [
      "crossbow"
    ],
    "effectText": [
      "",
      "+6% урона снаряда",
      "+12% урона снаряда",
      "+18% урона снаряда",
      "+24% урона снаряда"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 3,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:string",
        "count": 2,
        "label": "Нить"
      }
    ]
  },
  "quick_crank": {
    "name": "Механизм быстрой перезарядки",
    "category": "weapon",
    "icon": "minecraft:tripwire_hook",
    "max": 4,
    "description": "Ускоряет перезарядку ценой пикового урона.",
    "families": [
      "crossbow"
    ],
    "effectText": [
      "",
      "Быстрая перезарядка I",
      "Быстрая перезарядка II",
      "Быстрая перезарядка III",
      "Быстрая перезарядка IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:redstone",
        "count": 2,
        "label": "Редстоун"
      }
    ]
  },
  "penetrator_rail": {
    "name": "Пробивающая направляющая",
    "category": "weapon",
    "icon": "minecraft:spectral_arrow",
    "max": 4,
    "description": "Усиливает пробивную роль арбалета.",
    "families": [
      "crossbow"
    ],
    "conflictGroup": "crossbow_shot",
    "effectText": [
      "",
      "Пробитие I",
      "Пробитие II",
      "Пробитие III",
      "Пробитие IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:obsidian",
        "count": 1,
        "label": "Обсидиан"
      }
    ]
  },
  "split_guide": {
    "name": "Раздвоенная направляющая",
    "category": "weapon",
    "icon": "minecraft:arrow",
    "max": 4,
    "description": "Мультивыстрельная настройка; конфликтует с пробивной.",
    "families": [
      "crossbow"
    ],
    "conflictGroup": "crossbow_shot",
    "effectText": [
      "",
      "Разделение выстрела I",
      "Разделение выстрела II",
      "Разделение выстрела III",
      "Разделение выстрела IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:string",
        "count": 2,
        "label": "Нить"
      }
    ]
  },
  "harpoon_barb": {
    "name": "Гарпунный зацеп",
    "category": "weapon",
    "icon": "minecraft:trident",
    "max": 4,
    "description": "Усиливает контроль трезубца.",
    "families": [
      "trident"
    ],
    "effectText": [
      "",
      "Контроль трезубца I",
      "Контроль трезубца II",
      "Контроль трезубца III",
      "Контроль трезубца IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:prismarine_shard",
        "count": 3,
        "label": "Призмариновый осколок"
      },
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      }
    ]
  },
  "retrieval_cable": {
    "name": "Возвратный трос",
    "category": "weapon",
    "icon": "minecraft:lead",
    "max": 4,
    "description": "Физический аналог возврата брошенного оружия.",
    "families": [
      "trident",
      "chakram"
    ],
    "effectText": [
      "",
      "Возврат I",
      "Возврат II",
      "Возврат III",
      "Возврат IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:string",
        "count": 4,
        "label": "Нить"
      },
      {
        "ingredient": "minecraft:iron_nugget",
        "count": 4,
        "label": "Железный самородок"
      }
    ]
  },
  "hydrodynamic_head": {
    "name": "Гидродинамический наконечник",
    "category": "weapon",
    "icon": "minecraft:prismarine_crystals",
    "max": 4,
    "description": "Усиливает дальний удар под водой.",
    "families": [
      "trident"
    ],
    "effectText": [
      "",
      "+8% подводного урона",
      "+16% подводного урона",
      "+24% подводного урона",
      "+32% подводного урона"
    ],
    "base": [
      {
        "ingredient": "minecraft:prismarine_shard",
        "count": 4,
        "label": "Призмариновый осколок"
      },
      {
        "ingredient": "minecraft:quartz",
        "count": 1,
        "label": "Кварц"
      }
    ]
  },
  "conductive_crown": {
    "name": "Проводящая корона",
    "category": "weapon",
    "icon": "minecraft:lightning_rod",
    "max": 4,
    "description": "Грозовая специализация трезубца.",
    "families": [
      "trident"
    ],
    "effectText": [
      "",
      "Проводимость I",
      "Проводимость II",
      "Проводимость III",
      "Проводимость IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 4,
        "label": "Медный слиток"
      },
      {
        "ingredient": "minecraft:blaze_powder",
        "count": 1,
        "label": "Огненный порошок"
      }
    ]
  },
  "aggressive_geometry": {
    "name": "Агрессивная геометрия зубьев",
    "category": "tool",
    "icon": "minecraft:iron_pickaxe",
    "max": 4,
    "description": "Ускоряет добычу подходящим инструментом.",
    "families": [
      "pickaxe"
    ],
    "effectText": [
      "",
      "+10% скорости добычи",
      "+20% скорости добычи",
      "+30% скорости добычи",
      "+40% скорости добычи"
    ],
    "base": [
      {
        "ingredient": "minecraft:quartz",
        "count": 2,
        "label": "Кварц"
      },
      {
        "ingredient": "minecraft:flint",
        "count": 2,
        "label": "Кремень"
      }
    ]
  },
  "fracture_control": {
    "name": "Контроль разрушения",
    "category": "tool",
    "icon": "minecraft:raw_iron",
    "max": 4,
    "description": "Повышает выход подходящих руд; конфликтует с точной добычей.",
    "families": [
      "pickaxe"
    ],
    "conflictGroup": "pickaxe_yield",
    "effectText": [
      "",
      "+8% шанс доп. выхода",
      "+16% шанс доп. выхода",
      "+24% шанс доп. выхода",
      "+32% шанс доп. выхода"
    ],
    "base": [
      {
        "ingredient": "minecraft:amethyst_shard",
        "count": 2,
        "label": "Осколок аметиста"
      },
      {
        "ingredient": "minecraft:gold_ingot",
        "count": 1,
        "label": "Золото"
      }
    ]
  },
  "precision_extraction": {
    "name": "Прецизионная добыча",
    "category": "tool",
    "icon": "minecraft:diamond",
    "max": 4,
    "description": "Сохраняет подходящие блоки целиком; конфликтует с Контролем разрушения.",
    "families": [
      "pickaxe"
    ],
    "conflictGroup": "pickaxe_yield",
    "effectText": [
      "",
      "Точная добыча I",
      "Точная добыча II",
      "Точная добыча III",
      "Точная добыча IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:diamond",
        "count": 1,
        "label": "Алмаз"
      },
      {
        "ingredient": "minecraft:obsidian",
        "count": 2,
        "label": "Обсидиан"
      }
    ]
  },
  "reinforced_neck": {
    "name": "Усиленная шейка",
    "category": "tool",
    "icon": "minecraft:iron_ingot",
    "max": 4,
    "description": "Снижает обычный износ инструмента.",
    "families": [
      "pickaxe",
      "sickle"
    ],
    "effectText": [
      "",
      "−15% износа",
      "−25% износа",
      "−35% износа",
      "−45% износа"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 3,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:chain",
        "count": 1,
        "label": "Цепь"
      }
    ]
  },
  "wide_blade": {
    "name": "Широкое полотно",
    "category": "tool",
    "icon": "minecraft:iron_shovel",
    "max": 4,
    "description": "Ускоряет работу с землёй, песком и снегом.",
    "families": [
      "shovel"
    ],
    "effectText": [
      "",
      "+10% скорости",
      "+20% скорости",
      "+30% скорости",
      "+40% скорости"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 3,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:flint",
        "count": 1,
        "label": "Кремень"
      }
    ]
  },
  "trenching_edge": {
    "name": "Траншейная кромка",
    "category": "tool",
    "icon": "minecraft:stone_shovel",
    "max": 4,
    "description": "Ускоряет точную траншейную работу.",
    "families": [
      "shovel"
    ],
    "effectText": [
      "",
      "+8% точной скорости",
      "+16% точной скорости",
      "+24% точной скорости",
      "+32% точной скорости"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:quartz",
        "count": 1,
        "label": "Кварц"
      }
    ]
  },
  "reinforced_socket": {
    "name": "Усиленная втулка",
    "category": "tool",
    "icon": "minecraft:chain",
    "max": 4,
    "description": "Снижает износ инструмента.",
    "families": [
      "shovel"
    ],
    "effectText": [
      "",
      "−15% износа",
      "−25% износа",
      "−35% износа",
      "−45% износа"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 3,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:chain",
        "count": 1,
        "label": "Цепь"
      }
    ]
  },
  "harvest_teeth": {
    "name": "Урожайные зубья",
    "category": "tool",
    "icon": "minecraft:iron_hoe",
    "max": 4,
    "description": "Повышает выход подходящих культур.",
    "families": [
      "hoe"
    ],
    "effectText": [
      "",
      "+8% шанс доп. урожая",
      "+16% шанс доп. урожая",
      "+24% шанс доп. урожая",
      "+32% шанс доп. урожая"
    ],
    "base": [
      {
        "ingredient": "minecraft:gold_nugget",
        "count": 4,
        "label": "Золотой самородок"
      },
      {
        "ingredient": "minecraft:amethyst_shard",
        "count": 1,
        "label": "Осколок аметиста"
      }
    ]
  },
  "wide_cultivator": {
    "name": "Широкий культиватор",
    "category": "tool",
    "icon": "minecraft:diamond_hoe",
    "max": 4,
    "description": "Ускоряет обработку почвы.",
    "families": [
      "hoe"
    ],
    "effectText": [
      "",
      "+10% скорости работы",
      "+20% скорости работы",
      "+30% скорости работы",
      "+40% скорости работы"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 3,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 2,
        "label": "Медный слиток"
      }
    ]
  },
  "light_shaft": {
    "name": "Облегчённая рукоять",
    "category": "tool",
    "icon": "minecraft:stick",
    "max": 4,
    "description": "Ускоряет использование ценой ресурса.",
    "families": [
      "hoe"
    ],
    "effectText": [
      "",
      "+5% обращения",
      "+10% обращения",
      "+15% обращения",
      "+20% обращения"
    ],
    "base": [
      {
        "ingredient": "minecraft:stick",
        "count": 2,
        "label": "Палка"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 2,
        "label": "Кожа"
      }
    ]
  },
  "dual_angle": {
    "name": "Двухугловая головка",
    "category": "tool",
    "icon": "minecraft:iron_pickaxe",
    "max": 4,
    "description": "Универсальная работа по земле, дереву и камню.",
    "families": [
      "mattock"
    ],
    "effectText": [
      "",
      "+6% универсальной скорости",
      "+12% универсальной скорости",
      "+18% универсальной скорости",
      "+24% универсальной скорости"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 3,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:flint",
        "count": 2,
        "label": "Кремень"
      }
    ]
  },
  "reinforced_eye": {
    "name": "Усиленное ушко",
    "category": "tool",
    "icon": "minecraft:iron_nugget",
    "max": 4,
    "description": "Снижает структурный износ мотыги-кирки.",
    "families": [
      "mattock"
    ],
    "effectText": [
      "",
      "−15% износа",
      "−25% износа",
      "−35% износа",
      "−45% износа"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 3,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:chain",
        "count": 1,
        "label": "Цепь"
      }
    ]
  },
  "chisel_side": {
    "name": "Долотовая сторона",
    "category": "tool",
    "icon": "minecraft:stone_pickaxe",
    "max": 4,
    "description": "Усиливает работу по камню.",
    "families": [
      "mattock"
    ],
    "effectText": [
      "",
      "+10% по камню",
      "+20% по камню",
      "+30% по камню",
      "+40% по камню"
    ],
    "base": [
      {
        "ingredient": "minecraft:quartz",
        "count": 2,
        "label": "Кварц"
      },
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      }
    ]
  },
  "universal_balance": {
    "name": "Универсальный баланс",
    "category": "tool",
    "icon": "minecraft:diamond_pickaxe",
    "max": 4,
    "description": "Умеренно ускоряет все поддерживаемые работы paxel.",
    "families": [
      "paxel"
    ],
    "effectText": [
      "",
      "+6% общей скорости",
      "+12% общей скорости",
      "+18% общей скорости",
      "+24% общей скорости"
    ],
    "base": [
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 2,
        "label": "Медный слиток"
      },
      {
        "ingredient": "minecraft:quartz",
        "count": 2,
        "label": "Кварц"
      }
    ]
  },
  "reinforced_core": {
    "name": "Усиленный сердечник",
    "category": "tool",
    "icon": "minecraft:iron_block",
    "max": 4,
    "description": "Снижает износ paxel.",
    "families": [
      "paxel"
    ],
    "effectText": [
      "",
      "−15% износа",
      "−25% износа",
      "−35% износа",
      "−45% износа"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 4,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:chain",
        "count": 1,
        "label": "Цепь"
      }
    ]
  },
  "specialist_insert": {
    "name": "Специализированная вставка",
    "category": "tool",
    "icon": "minecraft:quartz",
    "max": 4,
    "description": "Сфокусированный бонус paxel; первая версия — камень.",
    "families": [
      "paxel"
    ],
    "effectText": [
      "",
      "+10% по камню",
      "+20% по камню",
      "+30% по камню",
      "+40% по камню"
    ],
    "base": [
      {
        "ingredient": "minecraft:quartz",
        "count": 2,
        "label": "Кварц"
      },
      {
        "ingredient": "minecraft:flint",
        "count": 2,
        "label": "Кремень"
      }
    ]
  },
  "reinforced_lip": {
    "name": "Усиленная кромка ковша",
    "category": "tool",
    "icon": "minecraft:iron_ingot",
    "max": 4,
    "description": "Снижает износ площадной добычи.",
    "families": [
      "excavator"
    ],
    "effectText": [
      "",
      "−15% износа",
      "−25% износа",
      "−35% износа",
      "−45% износа"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 4,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:chain",
        "count": 1,
        "label": "Цепь"
      }
    ]
  },
  "wide_cut": {
    "name": "Широкая геометрия реза",
    "category": "tool",
    "icon": "minecraft:iron_shovel",
    "max": 4,
    "description": "Ускоряет площадную работу ценой износа.",
    "families": [
      "excavator"
    ],
    "effectText": [
      "",
      "+10% скорости",
      "+20% скорости",
      "+30% скорости",
      "+40% скорости"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 3,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:flint",
        "count": 2,
        "label": "Кремень"
      }
    ]
  },
  "soil_channels": {
    "name": "Каналы выброса грунта",
    "category": "tool",
    "icon": "minecraft:dirt",
    "max": 4,
    "description": "Ускоряет работу по рыхлым материалам.",
    "families": [
      "excavator"
    ],
    "effectText": [
      "",
      "+12% по рыхлым блокам",
      "+24% по рыхлым блокам",
      "+36% по рыхлым блокам",
      "+48% по рыхлым блокам"
    ],
    "base": [
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 2,
        "label": "Медный слиток"
      },
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      }
    ]
  },
  "coarse_teeth": {
    "name": "Грубые зубья",
    "category": "tool",
    "icon": "minecraft:iron_axe",
    "max": 4,
    "description": "Ускоряют пиление дерева.",
    "families": [
      "saw"
    ],
    "effectText": [
      "",
      "+12% по дереву",
      "+24% по дереву",
      "+36% по дереву",
      "+48% по дереву"
    ],
    "base": [
      {
        "ingredient": "minecraft:flint",
        "count": 4,
        "label": "Кремень"
      },
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      }
    ]
  },
  "fine_teeth": {
    "name": "Точные зубья",
    "category": "tool",
    "icon": "minecraft:golden_axe",
    "max": 4,
    "description": "Более точный распил и вторичный выход.",
    "families": [
      "saw"
    ],
    "effectText": [
      "",
      "+5% шанс вторичного выхода",
      "+10% шанс вторичного выхода",
      "+15% шанс вторичного выхода",
      "+20% шанс вторичного выхода"
    ],
    "base": [
      {
        "ingredient": "minecraft:quartz",
        "count": 2,
        "label": "Кварц"
      },
      {
        "ingredient": "minecraft:gold_nugget",
        "count": 4,
        "label": "Золотой самородок"
      }
    ]
  },
  "hardened_spine": {
    "name": "Закалённый обух",
    "category": "tool",
    "icon": "minecraft:iron_ingot",
    "max": 4,
    "description": "Снижает износ пилы.",
    "families": [
      "saw"
    ],
    "effectText": [
      "",
      "−15% износа",
      "−25% износа",
      "−35% износа",
      "−45% износа"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 3,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:coal",
        "count": 2,
        "label": "Уголь"
      }
    ]
  },
  "fine_edge": {
    "name": "Точная кромка",
    "category": "tool",
    "icon": "minecraft:shears",
    "max": 4,
    "description": "Ускоряет стрижку, листву и паутину.",
    "families": [
      "shears"
    ],
    "effectText": [
      "",
      "+10% скорости",
      "+20% скорости",
      "+30% скорости",
      "+40% скорости"
    ],
    "base": [
      {
        "ingredient": "minecraft:quartz",
        "count": 2,
        "label": "Кварц"
      },
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 1,
        "label": "Железный слиток"
      }
    ]
  },
  "reinforced_pivot": {
    "name": "Усиленный шарнир",
    "category": "tool",
    "icon": "minecraft:iron_nugget",
    "max": 4,
    "description": "Снижает износ ножниц.",
    "families": [
      "shears"
    ],
    "effectText": [
      "",
      "−15% износа",
      "−25% износа",
      "−35% износа",
      "−45% износа"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 1,
        "label": "Медный слиток"
      }
    ]
  },
  "harvest_stop": {
    "name": "Ограничитель среза",
    "category": "tool",
    "icon": "minecraft:wheat_seeds",
    "max": 4,
    "description": "Повышает контролируемый растительный выход.",
    "families": [
      "shears"
    ],
    "effectText": [
      "",
      "+5% доп. растительного выхода",
      "+10%",
      "+15%",
      "+20%"
    ],
    "base": [
      {
        "ingredient": "minecraft:gold_nugget",
        "count": 4,
        "label": "Золотой самородок"
      },
      {
        "ingredient": "minecraft:amethyst_shard",
        "count": 1,
        "label": "Осколок аметиста"
      }
    ]
  },
  "wide_reaping": {
    "name": "Широкая дуга жатвы",
    "category": "tool",
    "icon": "minecraft:wheat",
    "max": 4,
    "description": "Ускоряет сбор культур и листвы.",
    "families": [
      "sickle"
    ],
    "effectText": [
      "",
      "+10% скорости жатвы",
      "+20%",
      "+30%",
      "+40%"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:flint",
        "count": 2,
        "label": "Кремень"
      }
    ]
  },
  "fine_harvest": {
    "name": "Точная жатвенная кромка",
    "category": "tool",
    "icon": "minecraft:golden_hoe",
    "max": 4,
    "description": "Повышает выход подходящих культур.",
    "families": [
      "sickle"
    ],
    "effectText": [
      "",
      "+8% шанс доп. урожая",
      "+16%",
      "+24%",
      "+32%"
    ],
    "base": [
      {
        "ingredient": "minecraft:gold_ingot",
        "count": 1,
        "label": "Золото"
      },
      {
        "ingredient": "minecraft:amethyst_shard",
        "count": 2,
        "label": "Осколок аметиста"
      }
    ]
  },
  "resonant_head": {
    "name": "Резонансная головка",
    "category": "tool",
    "icon": "minecraft:amethyst_shard",
    "max": 4,
    "description": "Усиливает дальность/читаемость геологоразведки.",
    "families": [
      "prospector"
    ],
    "effectText": [
      "",
      "Резонанс I",
      "Резонанс II",
      "Резонанс III",
      "Резонанс IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:amethyst_shard",
        "count": 3,
        "label": "Осколок аметиста"
      },
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      }
    ]
  },
  "focused_face": {
    "name": "Фокусированная грань",
    "category": "tool",
    "icon": "minecraft:diamond",
    "max": 4,
    "description": "Более узкое и точное сканирование.",
    "families": [
      "prospector"
    ],
    "effectText": [
      "",
      "Точность I",
      "Точность II",
      "Точность III",
      "Точность IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:diamond",
        "count": 1,
        "label": "Алмаз"
      },
      {
        "ingredient": "minecraft:quartz",
        "count": 2,
        "label": "Кварц"
      }
    ]
  },
  "reinforced_handle": {
    "name": "Усиленная рукоять",
    "category": "tool",
    "icon": "minecraft:stick",
    "max": 4,
    "description": "Снижает износ геологического молотка.",
    "families": [
      "prospector"
    ],
    "effectText": [
      "",
      "−15% износа",
      "−25%",
      "−35%",
      "−45%"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_ingot",
        "count": 2,
        "label": "Железный слиток"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 2,
        "label": "Кожа"
      }
    ]
  },
  "braided_line": {
    "name": "Плетёная леска",
    "category": "tool",
    "icon": "minecraft:string",
    "max": 4,
    "description": "Снижает износ удочки.",
    "families": [
      "fishing"
    ],
    "effectText": [
      "",
      "−15% износа",
      "−25%",
      "−35%",
      "−45%"
    ],
    "base": [
      {
        "ingredient": "minecraft:string",
        "count": 4,
        "label": "Нить"
      },
      {
        "ingredient": "minecraft:leather",
        "count": 1,
        "label": "Кожа"
      }
    ]
  },
  "weighted_float": {
    "name": "Утяжелённый поплавок",
    "category": "tool",
    "icon": "minecraft:iron_nugget",
    "max": 4,
    "description": "Стабилизирует и удлиняет заброс.",
    "families": [
      "fishing"
    ],
    "effectText": [
      "",
      "Стабильность I",
      "Стабильность II",
      "Стабильность III",
      "Стабильность IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:iron_nugget",
        "count": 4,
        "label": "Железный самородок"
      },
      {
        "ingredient": "minecraft:copper_ingot",
        "count": 1,
        "label": "Медный слиток"
      }
    ]
  },
  "fine_hook": {
    "name": "Точный крючок",
    "category": "tool",
    "icon": "minecraft:tripwire_hook",
    "max": 4,
    "description": "Смещает рыбалку к редкой добыче ценой клёва.",
    "families": [
      "fishing"
    ],
    "conflictGroup": "fishing_hook",
    "effectText": [
      "",
      "+1 удача рыбалки",
      "+2 удача рыбалки",
      "+3 удача рыбалки",
      "+4 удача рыбалки"
    ],
    "base": [
      {
        "ingredient": "minecraft:gold_nugget",
        "count": 4,
        "label": "Золотой самородок"
      },
      {
        "ingredient": "minecraft:amethyst_shard",
        "count": 1,
        "label": "Осколок аметиста"
      }
    ]
  },
  "fast_lure": {
    "name": "Быстрая приманка",
    "category": "tool",
    "icon": "minecraft:cod",
    "max": 4,
    "description": "Ускоряет клёв ценой редкой добычи.",
    "families": [
      "fishing"
    ],
    "conflictGroup": "fishing_hook",
    "effectText": [
      "",
      "Быстрый клёв I",
      "Быстрый клёв II",
      "Быстрый клёв III",
      "Быстрый клёв IV"
    ],
    "base": [
      {
        "ingredient": "minecraft:glow_berries",
        "count": 2,
        "label": "Светящиеся ягоды"
      },
      {
        "ingredient": "minecraft:string",
        "count": 2,
        "label": "Нить"
      }
    ]
  }
}
Object.keys(KOSH_FORGE_MODS).forEach(function(k) { KOSH_FORGE_MODS[k].id = k })

function koshForgePlayerKey(player) {
  try { return String(player.uuid) } catch (e) {}
  try { return String(player.getUUID()) } catch (e) {}
  return String(player.username)
}

function koshForgeStackId(stack) {
  try { return String(stack.id) } catch (e) {}
  try { return String(stack.getId()) } catch (e) {}
  return ''
}

function koshForgeHasTag(stack, tag) {
  try { return stack.hasTag(tag) } catch (e) {}
  try { return Ingredient.of('#' + tag).test(stack) } catch (e) {}
  return false
}

function koshForgeArmorTier(id) {
  var m = id.match(/_(i|ii|iii|iv)_test$/)
  if (!m) return 4
  if (m[1] === 'i') return 1
  if (m[1] === 'ii') return 2
  if (m[1] === 'iii') return 3
  return 4
}

function koshForgeArmorSlots(id, tier) {
  var chest = id.indexOf('_chestplate_') >= 0
  var legs = id.indexOf('_leggings_') >= 0

  if (tier <= 1) return 1
  if (tier === 2) return chest ? 2 : 1
  if (tier === 3) return 2
  return (chest || legs) ? 3 : 2
}

function koshForgeArmorPiece(id) {
  if (id.indexOf('_helmet_') >= 0) return 'helmet'
  if (id.indexOf('_chestplate_') >= 0) return 'chestplate'
  if (id.indexOf('_leggings_') >= 0) return 'leggings'
  if (id.indexOf('_boots_') >= 0) return 'boots'
  return 'unknown'
}

function koshForgeWeaponFamily(stack, id, namespace) {
  if (koshForgeHasTag(stack, 'minecraft:bows')) return 'bow'
  if (koshForgeHasTag(stack, 'minecraft:crossbows')) return 'crossbow'
  if (koshForgeHasTag(stack, 'minecraft:tridents')) return 'trident'

  var n = id.toLowerCase()
  if (n.indexOf('chakram') >= 0) return 'chakram'
  if (n.indexOf('twinblade') >= 0 || n.indexOf('warglaive') >= 0) return 'twinblade'
  if (n.indexOf('claymore') >= 0 || n.indexOf('greatsword') >= 0) return 'claymore'
  if (n.indexOf('rapier') >= 0) return 'rapier'
  if (n.indexOf('dagger') >= 0 || n.indexOf('knife') >= 0 || n.indexOf('_sai') >= 0 || n === 'sai') return 'dagger'
  if (n.indexOf('katana') >= 0) return 'katana'
  if (n.indexOf('machete') >= 0) return 'machete'
  if (n.indexOf('spear') >= 0 || n.indexOf('lance') >= 0) return 'spear'
  if (n.indexOf('glaive') >= 0 || n.indexOf('halberd') >= 0) return 'glaive'
  if (n.indexOf('scythe') >= 0) return 'scythe'
  if (n.indexOf('greataxe') >= 0 || koshForgeHasTag(stack, 'minecraft:axes')) return 'axe'
  if (n.indexOf('greathammer') >= 0 || n.indexOf('hammer') >= 0 || n.indexOf('mace') >= 0) return 'hammer'
  if (n.indexOf('slingshot') >= 0) return 'slingshot'
  if (koshForgeHasTag(stack, 'minecraft:swords')) return 'blade'

  // Simply Swords uniques without a readable standard type use the neutral rule.
  if (namespace === 'simplyswords') return 'unique'
  return null
}

function koshForgeToolFamily(stack, id) {
  var n = id.toLowerCase()
  if (n.indexOf('fishing_rod') >= 0 || koshForgeHasTag(stack, 'minecraft:fishing_rods')) return 'fishing'
  if (n.indexOf('prospector') >= 0 || n.indexOf('geologist') >= 0) return 'prospector'
  if (n.indexOf('excavator') >= 0) return 'excavator'
  if (n.indexOf('mattock') >= 0) return 'mattock'
  if (n.indexOf('paxel') >= 0) return 'paxel'
  if (n.indexOf('sickle') >= 0) return 'sickle'
  if (n.indexOf('saw') >= 0) return 'saw'
  if (n.indexOf('shears') >= 0 || id === 'minecraft:shears') return 'shears'
  if (koshForgeHasTag(stack, 'minecraft:pickaxes')) return 'pickaxe'
  if (koshForgeHasTag(stack, 'minecraft:shovels')) return 'shovel'
  if (koshForgeHasTag(stack, 'minecraft:hoes')) return 'hoe'
  return null
}

function koshForgeClassify(stack) {
  var id = koshForgeStackId(stack)
  if (!id || id === 'minecraft:air') return null

  var split = id.split(':')
  if (split.length === 2 && KOSH_ARMOR_NAMESPACES[split[0]]) {
    var armorTier = koshForgeArmorTier(split[1])
    return {
      category: 'armor',
      slots: koshForgeArmorSlots(split[1], armorTier),
      tier: armorTier,
      piece: koshForgeArmorPiece(split[1]),
      family: 'armor'
    }
  }

  var wf = koshForgeWeaponFamily(stack, split.length === 2 ? split[1] : id, split.length === 2 ? split[0] : '')
  if (wf) {
    var weaponSlots = (wf === 'dagger' || wf === 'rapier' || wf === 'chakram') ? 2 : 3
    if (wf === 'unique') weaponSlots = 1
    return { category: 'weapon', slots: weaponSlots, tier: 4, piece: 'mainhand', family: wf }
  }

  var tf = koshForgeToolFamily(stack, split.length === 2 ? split[1] : id)
  if (tf) return { category: 'tool', slots: 3, tier: 4, piece: 'mainhand', family: tf }

  return null
}
function koshForgeGetTag(stack) {
  try { return stack.getCustomData() } catch (e) {}
  return null
}

function koshForgeReadSlot(stack, slot) {
  var tag = koshForgeGetTag(stack)
  if (!tag) return null

  var id = ''
  var level = 0
  try { id = String(tag.getString('kosh_forge_slot_' + slot + '_id').orElse('')) } catch (e) {
    try { id = String(tag.getString('kosh_forge_slot_' + slot + '_id')) } catch (_e) {}
  }
  try { level = Number(tag.getInt('kosh_forge_slot_' + slot + '_level').orElse(0)) } catch (e) {
    try { level = Number(tag.getInt('kosh_forge_slot_' + slot + '_level')) } catch (_e) {}
  }

  if (!id || level <= 0) return null
  return { id: id, level: level }
}

function koshForgeWriteSlot(stack, slot, id, level) {
  var tag = koshForgeGetTag(stack)
  if (!tag) return false

  tag.putString('kosh_forge_version', '1')
  if (!id || level <= 0) {
    tag.remove('kosh_forge_slot_' + slot + '_id')
    tag.remove('kosh_forge_slot_' + slot + '_level')
  } else {
    tag.putString('kosh_forge_slot_' + slot + '_id', id)
    tag.putInt('kosh_forge_slot_' + slot + '_level', level)
  }

  try {
    stack.setCustomData(tag)
    return true
  } catch (e) {
    return false
  }
}

function koshForgeFindModLevel(stack, id) {
  for (var i = 0; i < 3; i++) {
    var s = koshForgeReadSlot(stack, i)
    if (s && s.id === id) return s.level
  }
  return 0
}


function koshForgeRoman(level) {
  return ['','I','II','III','IV'][Math.max(0, Math.min(4, level))] || '?'
}

function koshForgeEffectText(id, level) {
  var mod = KOSH_FORGE_MODS[id]
  if (!mod || !mod.effectText) return ''
  var i = Math.max(0, Math.min(mod.effectText.length - 1, level))
  return String(mod.effectText[i] || '')
}

function koshForgeCompatible(mod, stack, info) {
  if (!mod || !info || mod.category !== info.category) return false

  if (info.category === 'armor') {
    if (mod.pieces && mod.pieces.indexOf('all') < 0 && mod.pieces.indexOf(info.piece) < 0) return false
    if (mod.minArmorTier && info.tier < mod.minArmorTier) return false
  }

  if ((info.category === 'weapon' || info.category === 'tool') && mod.families) {
    if (mod.families.indexOf('all') < 0 && mod.families.indexOf(info.family) < 0) return false
  }

  if (info.family === 'unique' && info.category === 'weapon') {
    // Unique Simply Swords weapons get neutral handling/structure only.
    return mod.id === 'reinforced_frame' || mod.id === 'light_grip' || mod.id === 'tempered_structure'
  }

  return true
}

function koshForgeConflict(stack, info, modId, slotIndex) {
  var mod = KOSH_FORGE_MODS[modId]
  if (!mod || !mod.conflictGroup) return null
  for (var i = 0; i < info.slots; i++) {
    if (i === slotIndex) continue
    var s = koshForgeReadSlot(stack, i)
    if (!s) continue
    var other = KOSH_FORGE_MODS[s.id]
    if (other && other.conflictGroup && other.conflictGroup === mod.conflictGroup) return other
  }
  return null
}
function koshForgeManagedLoreSignature(stack, slots) {
  var parts = [String(slots)]
  for (var i = 0; i < slots; i++) {
    var s = koshForgeReadSlot(stack, i)
    parts.push(s ? (s.id + ':' + s.level) : '-')
  }
  return parts.join('|')
}

function koshForgeRefreshLore(stack, slots, force) {
  if (!stack || slots <= 0) return false

  var sig = koshForgeManagedLoreSignature(stack, slots)
  var tag = koshForgeGetTag(stack)
  if (!tag) return false

  var oldSig = ''
  try { oldSig = String(tag.getString('kosh_forge_lore_sig').orElse('')) } catch (e) {
    try { oldSig = String(tag.getString('kosh_forge_lore_sig')) } catch (_e) {}
  }
  if (!force && oldSig === sig) return true

  var lines = new KOSH_FORGE_ARRAY_LIST()

  // Preserve lore from the base item or other mods, but replace only our own managed lines.
  try {
    var oldLore = stack.get(KOSH_FORGE_DATA_COMPONENTS.LORE)
    if (oldLore) {
      var iterator = oldLore.lines().iterator()
      while (iterator.hasNext()) {
        var line = iterator.next()
        var plain = ''
        try { plain = String(line.getString()) } catch (e) {}
        if (plain.indexOf('Заточки: [') !== 0 && plain.indexOf('◆ Слот ') !== 0) lines.add(line)
      }
    }
  } catch (e) {}

  var glyphs = []
  for (var i = 0; i < slots; i++) {
    glyphs.push(koshForgeReadSlot(stack, i) ? '◆' : '◇')
  }

  lines.add(Text.yellow('Заточки: [' + glyphs.join('] [') + ']'))

  for (var j = 0; j < slots; j++) {
    var slot = koshForgeReadSlot(stack, j)
    if (!slot) continue
    var mod = KOSH_FORGE_MODS[slot.id]
    var modName = mod ? mod.name : slot.id
    var effect = koshForgeEffectText(slot.id, slot.level)
    var detail = '◆ Слот ' + (j + 1) + ': ' + modName + ' ' + koshForgeRoman(slot.level)
    if (effect) detail += ' — ' + effect
    lines.add(Text.aqua(detail))
  }

  try {
    stack.set(KOSH_FORGE_DATA_COMPONENTS.LORE, new KOSH_FORGE_ITEM_LORE(lines))
    tag.putString('kosh_forge_lore_sig', sig)
    stack.setCustomData(tag)
    return true
  } catch (e) {
    return false
  }
}

function koshForgeLevelCost(mod, nextLevel) {
  var out = []
  for (var i = 0; i < mod.base.length; i++) out.push(mod.base[i])

  if (mod.costMode === 'soul') {
    if (nextLevel === 1) {
      out.push({ ingredient: 'kubejs:heat_resistant_binder', count: 1, label: 'Жаростойкая связка' })
      out.push({ ingredient: '#c:ingots/crimson_steel', count: 1, label: 'Багровая сталь' })
    } else if (nextLevel === 2) {
      out.push({ ingredient: 'kubejs:heat_resistant_binder', count: 2, label: 'Жаростойкая связка' })
      out.push({ ingredient: '#c:ingots/crimson_steel', count: 2, label: 'Багровая сталь' })
    } else if (nextLevel === 3) {
      out.push({ ingredient: 'kubejs:finishing_abrasive', count: 1, label: 'Финишный абразив' })
      out.push({ ingredient: '#c:ingots/tyrian_steel', count: 1, label: 'Тириановая сталь' })
    } else if (nextLevel === 4) {
      out.push({ ingredient: 'kubejs:finishing_abrasive', count: 2, label: 'Финишный абразив' })
      out.push({ ingredient: '#c:ingots/tyrian_steel', count: 2, label: 'Тириановая сталь' })
    }
    return out
  }

  if (mod.costMode === 'step') {
    out.push({ ingredient: 'create:precision_mechanism', count: 1, label: 'Точный механизм' })
    out.push({ ingredient: '#c:ingots/steel', count: 2, label: 'Сталь' })
    out.push({ ingredient: 'kubejs:industrial_abrasive', count: 1, label: 'Промышленный абразив' })
    return out
  }

  if (mod.costMode === 'quiet') {
    out.push({ ingredient: '#c:ingots/steel', count: 2, label: 'Сталь' })
    out.push({ ingredient: 'kubejs:industrial_abrasive', count: 1, label: 'Промышленный абразив' })
    return out
  }

  if (nextLevel === 1) {
    out.push({ ingredient: 'kubejs:base_abrasive', count: 1, label: 'Базовый абразив' })
  } else if (nextLevel === 2) {
    out.push({ ingredient: 'kubejs:industrial_abrasive', count: 1, label: 'Промышленный абразив' })
    out.push({ ingredient: '#c:ingots/steel', count: 1, label: 'Сталь' })
  } else if (nextLevel === 3) {
    out.push({ ingredient: 'kubejs:heat_resistant_binder', count: 1, label: 'Жаростойкая связка' })
    out.push({ ingredient: '#c:ingots/crimson_steel', count: 1, label: 'Багровая сталь' })
  } else if (nextLevel === 4) {
    out.push({ ingredient: 'kubejs:finishing_abrasive', count: 1, label: 'Финишный абразив' })
    out.push({ ingredient: '#c:ingots/tyrian_steel', count: 1, label: 'Тириановая сталь' })
  }

  return out
}
function koshForgeIngredient(spec) {
  try { return Ingredient.of(spec) } catch (e) { return null }
}

function koshForgeInventoryCount(player, spec) {
  var ingredient = koshForgeIngredient(spec)
  if (!ingredient) return 0
  var inv = player.inventory
  var total = 0

  for (var i = 0; i < inv.getSlots(); i++) {
    var stack = inv.getStackInSlot(i)
    try {
      if (!stack.empty && ingredient.test(stack)) total += stack.count
    } catch (e) {}
  }
  return total
}

function koshForgeCanPay(player, cost) {
  for (var i = 0; i < cost.length; i++) {
    if (koshForgeInventoryCount(player, cost[i].ingredient) < cost[i].count) return false
  }
  return true
}

function koshForgeConsume(player, spec, amount) {
  var ingredient = koshForgeIngredient(spec)
  if (!ingredient) return false
  var inv = player.inventory
  var left = amount

  for (var i = 0; i < inv.getSlots() && left > 0; i++) {
    var stack = inv.getStackInSlot(i)
    var matches = false
    try { matches = !stack.empty && ingredient.test(stack) } catch (e) {}
    if (!matches) continue

    var take = Math.min(left, stack.count)
    inv.extractItem(i, take, false)
    left -= take
  }

  return left <= 0
}

function koshForgePay(player, cost) {
  if (!koshForgeCanPay(player, cost)) return false
  for (var i = 0; i < cost.length; i++) {
    if (!koshForgeConsume(player, cost[i].ingredient, cost[i].count)) return false
  }
  return true
}

function koshForgeCostText(cost) {
  var parts = []
  for (var i = 0; i < cost.length; i++) parts.push(cost[i].count + '× ' + cost[i].label)
  return parts.join(' • ')
}

function koshForgeLiveTarget(player, session) {
  var inv = player.inventory
  if (!inv) return null

  var stack = null
  try { stack = inv.getStackInSlot(session.selectedSlot) } catch (e) { return null }
  if (!stack) return null

  try { if (stack.empty) return null } catch (e) {}
  if (koshForgeStackId(stack) !== session.targetId) return null
  return stack
}

function koshForgeCommitTarget(player, session, stack) {
  try {
    player.inventory.setStackInSlot(session.selectedSlot, stack)
    try { player.sendInventoryUpdate() } catch (e) {}
    return true
  } catch (e) {
    return false
  }
}

function koshForgeAbort(player, key, message) {
  if (message) player.tell(message)
  delete KOSH_FORGE_SESSIONS[key]
}

function koshForgeFinalize(player, key, attempt) {
  var session = KOSH_FORGE_SESSIONS[key]
  if (!session || session.finished) return

  // CustomChestMenu temporarily captures the real player inventory.
  // Never touch the target or payment until that inventory has been restored.
  var liveTarget = koshForgeLiveTarget(player, session)
  if (!liveTarget) {
    if (attempt < 20) {
      player.server.scheduleInTicks(1, function() {
        koshForgeFinalize(player, key, attempt + 1)
      })
      return
    }

    // Fail closed: the bench never removed the item, so aborting cannot delete it.
    koshForgeAbort(player, key, Text.red('Кузница не дождалась восстановления инвентаря. Предмет не изменён.'))
    return
  }

  session.finished = true
  var pending = session.pending

  // Closing the GUI without selecting an action is a pure no-op.
  if (!pending) {
    var noOpInfo = koshForgeClassify(liveTarget)
    if (noOpInfo && noOpInfo.category === 'armor') {
      koshForgeRefreshLore(liveTarget, noOpInfo.slots, false)
      koshForgeCommitTarget(player, session, liveTarget)
    }
    delete KOSH_FORGE_SESSIONS[key]
    return
  }

  if (pending.kind === 'remove') {
    var removed = liveTarget.copy()
    if (!koshForgeWriteSlot(removed, pending.slot, '', 0)) {
      koshForgeAbort(player, key, Text.red('Не удалось изменить данные предмета. Предмет оставлен без изменений.'))
      return
    }

    koshForgeRefreshLore(removed, koshForgeClassify(removed).slots, true)

    if (!koshForgeCommitTarget(player, session, removed)) {
      koshForgeAbort(player, key, Text.red('Не удалось сохранить изменение. Предмет оставлен без изменений.'))
      return
    }

    player.tell(Text.yellow('Заточка снята. Материалы не возвращены.'))
    delete KOSH_FORGE_SESSIONS[key]
    return
  }

  var mod = KOSH_FORGE_MODS[pending.modId]
  var info = koshForgeClassify(liveTarget)
  if (!mod || !info || mod.category !== info.category) {
    koshForgeAbort(player, key, Text.red('Эта модификация несовместима с предметом.'))
    return
  }

  var current = koshForgeReadSlot(liveTarget, pending.slot)
  var nextLevel = current && current.id === pending.modId ? current.level + 1 : 1

  if (nextLevel > mod.max) {
    koshForgeAbort(player, key, Text.yellow('У этой заточки уже максимальный уровень.'))
    return
  }

  if (info.category === 'armor' && nextLevel > info.tier) {
    koshForgeAbort(player, key, Text.red('Уровень заточки не может быть выше уровня этой брони.'))
    return
  }

  if (!koshForgeCompatible(mod, liveTarget, info)) {
    koshForgeAbort(player, key, Text.red('Эта обработка не подходит этому типу предмета.'))
    return
  }

  if (info.category === 'armor' && mod.levelMinArmorTier) {
    var minTier = Number(mod.levelMinArmorTier[nextLevel] || 1)
    if (info.tier < minTier) {
      koshForgeAbort(player, key, Text.red('Для этого уровня заточки нужна броня не ниже уровня ' + koshForgeRoman(minTier) + '.'))
      return
    }
  }

  for (var i = 0; i < info.slots; i++) {
    if (i === pending.slot) continue
    var other = koshForgeReadSlot(liveTarget, i)
    if (other && other.id === pending.modId) {
      koshForgeAbort(player, key, Text.red('Одинаковая заточка не может занимать два слота.'))
      return
    }
  }

  var conflict = koshForgeConflict(liveTarget, info, pending.modId, pending.slot)
  if (conflict) {
    koshForgeAbort(player, key, Text.red('Конфликт обработок: ' + mod.name + ' ↔ ' + conflict.name))
    return
  }

  var cost = koshForgeLevelCost(mod, nextLevel)
  if (!koshForgeCanPay(player, cost)) {
    koshForgeAbort(player, key, Text.red('Не хватает материалов: ' + koshForgeCostText(cost)))
    return
  }

  // Prepare the result BEFORE payment. If custom_data cannot be written,
  // the player loses neither materials nor the target item.
  var modified = liveTarget.copy()
  if (!koshForgeWriteSlot(modified, pending.slot, pending.modId, nextLevel)) {
    koshForgeAbort(player, key, Text.red('Не удалось записать заточку. Материалы не потрачены.'))
    return
  }

  koshForgeRefreshLore(modified, info.slots, true)

  if (!koshForgePay(player, cost)) {
    koshForgeAbort(player, key, Text.red('Не удалось списать материалы. Предмет оставлен без изменений.'))
    return
  }

  if (!koshForgeCommitTarget(player, session, modified)) {
    // This path should not occur after a successful inventory-restore probe.
    // Do not silently lose the item: give the prepared copy back.
    try { player.give(modified) } catch (e) {}
    koshForgeAbort(player, key, Text.red('Не удалось вернуть предмет в исходный слот; обработанный предмет выдан в инвентарь.'))
    return
  }

  player.tell(Text.green(mod.name + ' ' + ['','I','II','III','IV'][nextLevel] + ' установлена.'))
  delete KOSH_FORGE_SESSIONS[key]
}

function koshForgeQueueFinalize(player, key) {
  var session = KOSH_FORGE_SESSIONS[key]
  if (!session || session.returnScheduled) return
  session.returnScheduled = true

  // Two ticks is the normal path; finalize also retries until the captured
  // inventory has actually been restored.
  player.server.scheduleInTicks(2, function() {
    koshForgeFinalize(player, key, 0)
  })
}

function koshForgeOpenModifierPage(player, key, slotIndex) {
  var session = KOSH_FORGE_SESSIONS[key]
  if (!session) return
  var info = koshForgeClassify(session.preview)
  if (!info) return

  player.openChestGUI(Text.of('Кузнечный стенд'), 6, function(gui) {
    gui.playerSlots = false

    gui.button(4, 0, session.preview.copy(), Text.gold('Обрабатываемый предмет'), function(e) {
      e.setHandled()
    })

    var current = koshForgeReadSlot(session.preview, slotIndex)
    if (current) {
      var cm = KOSH_FORGE_MODS[current.id]
      var removeIcon = Item.of('minecraft:barrier')
      gui.button(8, 5, removeIcon, Text.red('Снять: ' + (cm ? cm.name : current.id)), function(e) {
        session.pending = { kind: 'remove', slot: slotIndex }
        player.closeMenu()
      })
    }

    var candidates = []
    Object.keys(KOSH_FORGE_MODS).forEach(function(modId) {
      var mod = KOSH_FORGE_MODS[modId]
      if (koshForgeCompatible(mod, session.preview, info)) candidates.push(modId)
    })

    for (var ci = 0; ci < candidates.length && ci < 28; ci++) {
      ;(function(modId, index) {
        var mod = KOSH_FORGE_MODS[modId]
        var installed = current && current.id === modId ? current.level : 0
        var next = installed + 1
        var label = mod.name + ' ' + (next <= mod.max ? koshForgeRoman(next) : 'MAX')
        var icon = Item.of(mod.icon)
        var gx = 1 + (index % 7)
        var gy = 1 + Math.floor(index / 7)

        gui.button(gx, gy, icon, Text.aqua(label), function(e) {
          if (next > mod.max) {
            player.tell(Text.yellow('Уже максимальный уровень.'))
            return
          }

          var conflict = koshForgeConflict(session.preview, info, modId, slotIndex)
          if (conflict) {
            player.tell(Text.red('Конфликт: ' + mod.name + ' ↔ ' + conflict.name))
            return
          }

          var cost = koshForgeLevelCost(mod, next)
          var effect = koshForgeEffectText(modId, next)
          player.tell(Text.gray(mod.description))
          if (effect) player.tell(Text.aqua(effect))
          player.tell(Text.gray('Цена: ' + koshForgeCostText(cost)))
          session.pending = { kind: 'apply', slot: slotIndex, modId: modId }
          player.closeMenu()
        })
      })(candidates[ci], ci)
    }

    gui.button(0, 5, Item.of('minecraft:arrow'), Text.yellow('Назад'), function(e) {
      koshForgeOpenMain(player, key)
    })

    gui.closed = function() {
      koshForgeQueueFinalize(player, key)
    }
  })
}

function koshForgeOpenMain(player, key) {
  var session = KOSH_FORGE_SESSIONS[key]
  if (!session) return
  var info = koshForgeClassify(session.preview)
  if (!info) return

  player.openChestGUI(Text.of('Кузнечный стенд'), 6, function(gui) {
    gui.playerSlots = false

    gui.button(4, 0, session.preview.copy(), Text.gold('Обрабатываемый предмет'), function(e) {
      e.setHandled()
    })

    for (var i = 0; i < info.slots; i++) {
      ;(function(slotIndex) {
        var current = koshForgeReadSlot(session.preview, slotIndex)
        var icon
        var name

        if (current && KOSH_FORGE_MODS[current.id]) {
          icon = Item.of(KOSH_FORGE_MODS[current.id].icon)
          name = 'Слот ' + (slotIndex + 1) + ': ' + KOSH_FORGE_MODS[current.id].name + ' ' + ['','I','II','III','IV'][current.level]
        } else {
          icon = Item.of('minecraft:gray_dye')
          name = 'Слот ' + (slotIndex + 1) + ': свободен'
        }

        gui.button(2 + slotIndex * 2, 2, icon, Text.aqua(name), function(e) {
          koshForgeOpenModifierPage(player, key, slotIndex)
        })
      })(i)
    }

    gui.button(4, 4, Item.of('minecraft:book'), Text.gray('ЛКМ по слоту — выбрать или улучшить. На следующем экране можно снять заточку.'), function(e) {
      e.setHandled()
    })

    gui.closed = function() {
      koshForgeQueueFinalize(player, key)
    }
  })
}

PlayerEvents.tick(event => {
  var player = event.player
  try {
    if ((player.tickCount % 20) !== 0) return
  } catch (e) {
    return
  }

  var inv = player.inventory
  if (!inv) return

  for (var i = 0; i < inv.getSlots(); i++) {
    var stack = inv.getStackInSlot(i)
    var info = koshForgeClassify(stack)
    if (!info) continue

    var shouldManage = info.category === 'armor'
    if (!shouldManage) {
      var tag = koshForgeGetTag(stack)
      try { shouldManage = tag && String(tag.getString('kosh_forge_version').orElse('')) === '1' } catch (e) {}
    }

    if (shouldManage) koshForgeRefreshLore(stack, info.slots, false)
  }
})

BlockEvents.rightClicked('kubejs:forge_bench', event => {
  var player = event.player
  if (!player || !player.isServerPlayer()) return

  var held = player.mainHandItem
  var info = koshForgeClassify(held)
  if (!info) {
    player.tell(Text.red('Возьми в основную руку броню, оружие или инструмент для обработки.'))
    event.cancel()
    return
  }

  var key = koshForgePlayerKey(player)
  if (KOSH_FORGE_SESSIONS[key]) {
    player.tell(Text.yellow('Предыдущая операция кузницы ещё не завершена.'))
    event.cancel()
    return
  }

  var preview = held.copy()
  preview.count = 1
  var selected = player.selectedSlot

  // Critical safety rule: never remove the target before opening CustomChestMenu.
  // KubeJS itself captures/restores the inventory while the GUI is open.
  // We keep only a preview and the original slot/id, then modify the live stack
  // after inventory restoration.
  KOSH_FORGE_SESSIONS[key] = {
    preview: preview,
    targetId: koshForgeStackId(held),
    selectedSlot: selected,
    pending: null,
    returnScheduled: false,
    finished: false
  }

  koshForgeOpenMain(player, key)
  event.cancel()
})
