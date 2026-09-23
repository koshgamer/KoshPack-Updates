// KoshPack professional armor crafting components.
// Runtime item registrations for the 17-profession I -> IV armor progression.
// Physical armor bases are no longer fixed KubeJS reinforcements: all four tiers
// consume material-bearing Silent Gear plates cast in SGear Metalworks.

const KOSHPACK_PROFESSIONS = [
  { id: 'miner', ru: 'Шахтёр', texture: 'minecraft:item/iron_pickaxe' },
  { id: 'engineer', ru: 'Инженер', texture: 'minecraft:item/redstone' },
  { id: 'scout', ru: 'Разведчик', texture: 'minecraft:item/spyglass' },
  { id: 'builder', ru: 'Строитель', texture: 'minecraft:item/brick' },
  { id: 'medic', ru: 'Медик', texture: 'minecraft:item/honey_bottle' },
  { id: 'farmer', ru: 'Фермер', texture: 'minecraft:item/wheat' },
  { id: 'blacksmith', ru: 'Кузнец', texture: 'minecraft:item/iron_ingot' },
  { id: 'fisher', ru: 'Рыбак', texture: 'minecraft:item/fishing_rod' },
  { id: 'lumberjack', ru: 'Лесоруб', texture: 'minecraft:item/iron_axe' },
  { id: 'diver', ru: 'Водолаз', texture: 'minecraft:item/nautilus_shell' },
  { id: 'fighter', ru: 'Боец', texture: 'minecraft:item/iron_sword' },
  { id: 'archer', ru: 'Лучник', texture: 'minecraft:item/bow' },
  { id: 'shooter', ru: 'Стрелок', texture: 'minecraft:item/crossbow' },
  { id: 'artillery', ru: 'Артиллерист', texture: 'minecraft:item/firework_rocket' },
  { id: 'hunter', ru: 'Охотник', texture: 'minecraft:item/bone' },
  { id: 'researcher', ru: 'Исследователь', texture: 'minecraft:item/compass' },
  { id: 'pilot', ru: 'Пилот', texture: 'minecraft:item/elytra' }
]

StartupEvents.registry('item', event => {
  // Cast armor plates come from Silent Gear Metalworks and already carry material data.

  // One physical profession module is consumed per upgraded armor piece.
  // Higher modules are built from the previous module, so module progression is sequential too.
  KOSHPACK_PROFESSIONS.forEach(prof => {
    event.create(`${prof.id}_module_i`)
      .displayName(`Профессиональный модуль: ${prof.ru} • I`)
      .maxStackSize(16)
      .texture(prof.texture)

    event.create(`${prof.id}_module_ii`)
      .displayName(`Профессиональный модуль: ${prof.ru} • II`)
      .maxStackSize(16)
      .rarity('uncommon')
      .texture(prof.texture)

    event.create(`${prof.id}_module_iii`)
      .displayName(`Промышленный модуль: ${prof.ru} • III`)
      .maxStackSize(16)
      .rarity('rare')
      .texture(prof.texture)

    event.create(`${prof.id}_module_iv`)
      .displayName(`Мастерский модуль: ${prof.ru} • IV`)
      .maxStackSize(16)
      .rarity('epic')
      .texture(prof.texture)
  })
})
