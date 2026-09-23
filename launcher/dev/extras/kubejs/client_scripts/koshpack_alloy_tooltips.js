// KoshPack alloy progression tooltips v1.
// Two compact lines only: progression stage + practical role/next step.

var KOSH_ALLOY_TOOLTIP = {
  'create:brass_ingot': [
    'Металлургия KoshPack • этап I',
    'Медь + цинк • лёгкий и быстрый материал'
  ],
  'createmetallurgy:steel_ingot': [
    'Металлургия KoshPack • этап I',
    'Железо + углерод • прочная рабочая основа'
  ],
  'minecraft:netherite_ingot': [
    'Металлургия KoshPack • этап II',
    'Древние обломки + золото • покрытие и жаростойкость'
  ],
  'silentgear:blaze_gold_ingot': [
    'Металлургия KoshPack • этап II',
    'Золото + ифрит • очень быстро, но хрупко'
  ],
  'silentgear:crimson_iron_ingot': [
    'Металлургия KoshPack • этап II',
    'Редкий металл • основа для багровой стали'
  ],
  'silentgear:azure_silver_ingot': [
    'Металлургия KoshPack • этап II',
    'Редкий металл • основа для азуритового электрума'
  ],
  'silentgear:crimson_steel_ingot': [
    'Металлургия KoshPack • этап III',
    'Багровое железо + огненные компоненты • прочность и жар'
  ],
  'silentgear:azure_electrum_ingot': [
    'Металлургия KoshPack • этап III',
    'Азуритовое серебро + золото + эндер • максимальная скорость'
  ],
  'silentgear:tyrian_steel_ingot': [
    'Металлургия KoshPack • этап IV',
    'Багровая сталь + азуритовый электрум • универсальный эндгейм'
  ],
  'sgearmetalworks:uru_metal_ingot': [
    'Металлургия KoshPack • этап V',
    'Тирийская сталь + редкие расплавы • абсолютный эндгейм'
  ]
}

ItemEvents.modifyTooltips(function(event) {
  Object.keys(KOSH_ALLOY_TOOLTIP).forEach(function(itemId) {
    var lines = KOSH_ALLOY_TOOLTIP[itemId]
    event.add(itemId, Text.gold(lines[0]))
    event.add(itemId, Text.darkGray(lines[1]))
  })
})
