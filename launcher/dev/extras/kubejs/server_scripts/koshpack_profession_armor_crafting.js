// KoshPack professional armor crafting runtime v2.
// 17 professions x 4 armor pieces x 4 tiers.
//
// Physical construction:
// - every tier consumes a material-bearing Silent Gear armor plate cast in SGear Metalworks;
// - the professional module determines profession/tier;
// - the cast plate determines armor, toughness, knockback resistance and durability;
// - II -> IV also consume the previous armor piece, preserving its forge/enchantment state.
//
// All four tiers are assembled at the workbench so the newly cast plate can intentionally
// replace the previous physical material during an upgrade.

const ARMOR_PIECES = [
  { id: 'helmet', tier1Extra: ['minecraft:leather', 'minecraft:string'] },
  { id: 'chestplate', tier1Extra: ['2x minecraft:leather', '2x minecraft:white_wool'] },
  { id: 'leggings', tier1Extra: ['2x minecraft:leather', 'minecraft:white_wool'] },
  { id: 'boots', tier1Extra: ['2x minecraft:leather'] }
]

const ARMOR_BASE_PARTS = {
  helmet: 'silentgear:helmet_plates',
  chestplate: 'silentgear:chestplate_plates',
  leggings: 'silentgear:legging_plates',
  boots: 'silentgear:boot_plates'
}

const ARMOR_TIER_CHAIN = [
  { id: 'ii', prev: 'i' },
  { id: 'iii', prev: 'ii' },
  { id: 'iv', prev: 'iii' }
]

const PROFESSIONS = [
  {
    id: 'miner', namespace: 'koshpackminerhelmet', itemPrefix: 'miner',
    moduleI: ['3x minecraft:flint', '2x minecraft:copper_ingot', '2x minecraft:coal'],
    moduleII: ['minecraft:lantern', '2x minecraft:iron_ingot'],
    moduleIII: ['create:precision_mechanism', 'minecraft:quartz', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:diamond']
  },
  {
    id: 'engineer', namespace: 'koshpackengineerhelmet', itemPrefix: 'engineer',
    moduleI: ['3x minecraft:copper_ingot', '3x minecraft:redstone', '2x minecraft:iron_ingot'],
    moduleII: ['create:precision_mechanism', '2x minecraft:copper_ingot'],
    moduleIII: ['create:precision_mechanism', 'minecraft:redstone_block', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'create:precision_mechanism']
  },
  {
    id: 'scout', namespace: 'koshpackscouthelmet', itemPrefix: 'scout',
    moduleI: ['minecraft:spyglass', '2x minecraft:leather', '2x minecraft:feather', 'minecraft:string'],
    moduleII: ['minecraft:spyglass', 'minecraft:compass'],
    moduleIII: ['create:brass_sheet', 'minecraft:ender_pearl', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:echo_shard']
  },
  {
    id: 'builder', namespace: 'koshpackbuilderhelmet', itemPrefix: 'builder',
    moduleI: ['3x minecraft:brick', '2x minecraft:string', '2x minecraft:iron_ingot'],
    moduleII: ['minecraft:scaffolding', '2x minecraft:iron_ingot'],
    moduleIII: ['create:precision_mechanism', 'minecraft:quartz', 'minecraft:magma_cream'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:diamond']
  },
  {
    id: 'medic', namespace: 'koshpackmedichelmet', itemPrefix: 'medic',
    moduleI: ['3x minecraft:white_wool', '2x minecraft:paper', 'minecraft:honey_bottle', 'minecraft:gold_ingot'],
    moduleII: ['minecraft:honey_bottle', 'minecraft:golden_carrot'],
    moduleIII: ['minecraft:ghast_tear', 'minecraft:blaze_powder', 'create:brass_sheet'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:ghast_tear']
  },
  {
    id: 'farmer', namespace: 'koshpackfarmerhelmet', itemPrefix: 'farmer',
    moduleI: ['3x minecraft:wheat', '2x minecraft:leather', '2x minecraft:string'],
    moduleII: ['minecraft:shears', 'minecraft:iron_hoe'],
    moduleIII: ['create:brass_sheet', 'minecraft:golden_carrot', 'minecraft:magma_cream'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:golden_carrot']
  },
  {
    id: 'blacksmith', namespace: 'koshpackblacksmithhelmet', itemPrefix: 'blacksmith',
    moduleI: ['3x minecraft:brick', '2x minecraft:coal', '2x minecraft:leather'],
    moduleII: ['minecraft:blast_furnace', 'minecraft:iron_ingot'],
    moduleIII: ['minecraft:blaze_rod', 'minecraft:magma_cream', 'create:brass_sheet'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:netherite_scrap']
  },
  {
    id: 'fisher', namespace: 'koshpackfisherhelmet', itemPrefix: 'fisher',
    moduleI: ['3x minecraft:string', '2x minecraft:cod', '2x minecraft:leather'],
    moduleII: ['minecraft:fishing_rod', 'minecraft:prismarine_shard'],
    moduleIII: ['create:brass_sheet', 'minecraft:prismarine_crystals', 'minecraft:magma_cream'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:heart_of_the_sea']
  },
  {
    id: 'lumberjack', namespace: 'koshpacklumberjackhelmet', itemPrefix: 'lumberjack',
    moduleI: ['3x minecraft:oak_log', '2x minecraft:iron_ingot', '2x minecraft:leather'],
    moduleII: ['minecraft:iron_axe', 'minecraft:chain'],
    moduleIII: ['create:brass_sheet', 'minecraft:diamond', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:diamond_axe']
  },
  {
    id: 'diver', namespace: 'koshpackdiverhelmet', itemPrefix: 'diver',
    moduleI: ['3x minecraft:copper_ingot', '2x minecraft:glass', '2x minecraft:dried_kelp'],
    moduleII: ['minecraft:nautilus_shell', 'minecraft:glass', 'minecraft:copper_ingot'],
    moduleIII: ['create:copper_backtank', 'minecraft:heart_of_the_sea', 'minecraft:magma_cream'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:heart_of_the_sea']
  },
  {
    id: 'fighter', namespace: 'koshpackfighterarmor', itemPrefix: 'fighter',
    moduleI: ['3x minecraft:iron_ingot', '2x minecraft:leather', '2x minecraft:flint'],
    moduleII: ['minecraft:shield', 'minecraft:iron_ingot'],
    moduleIII: ['minecraft:blaze_rod', 'minecraft:diamond', 'create:brass_sheet'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:netherite_scrap']
  },
  {
    id: 'archer', namespace: 'koshpackarcherarmor', itemPrefix: 'archer',
    moduleI: ['3x minecraft:feather', '3x minecraft:string', '2x minecraft:leather'],
    moduleII: ['minecraft:bow', 'minecraft:leather'],
    moduleIII: ['create:brass_sheet', 'minecraft:phantom_membrane', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:ender_eye']
  },
  {
    id: 'shooter', namespace: 'koshpackshooterarmor', itemPrefix: 'shooter',
    moduleI: ['3x minecraft:gunpowder', '2x minecraft:copper_ingot', '2x minecraft:iron_ingot'],
    moduleII: ['minecraft:crossbow', 'minecraft:iron_ingot'],
    moduleIII: ['create:brass_sheet', 'minecraft:spyglass', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:spyglass']
  },
  {
    id: 'artillery', namespace: 'koshpackartilleryarmor', itemPrefix: 'artillery',
    moduleI: ['3x minecraft:gunpowder', '3x minecraft:brick', '2x minecraft:iron_ingot'],
    moduleII: ['minecraft:tnt', 'minecraft:iron_ingot'],
    moduleIII: ['minecraft:blaze_rod', '2x minecraft:tnt', 'create:brass_sheet'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:netherite_scrap']
  },
  {
    id: 'hunter', namespace: 'koshpackhunterarmor', itemPrefix: 'hunter',
    moduleI: ['3x minecraft:leather', '2x minecraft:bone', '2x minecraft:string'],
    moduleII: ['minecraft:spyglass', 'minecraft:lead'],
    moduleIII: ['create:brass_sheet', 'minecraft:rabbit_hide', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:echo_shard']
  },
  {
    id: 'researcher', namespace: 'koshpackresearcherarmor', itemPrefix: 'researcher',
    moduleI: ['minecraft:compass', '3x minecraft:paper', '2x minecraft:leather'],
    moduleII: ['minecraft:spyglass', 'minecraft:compass'],
    moduleIII: ['create:brass_sheet', 'minecraft:amethyst_shard', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:echo_shard']
  },
  {
    id: 'pilot', namespace: 'koshpackpilothelmet', itemPrefix: 'pilot',
    moduleI: ['2x minecraft:glass', '3x minecraft:string', '2x minecraft:copper_ingot'],
    moduleII: ['create:precision_mechanism', 'minecraft:phantom_membrane'],
    moduleIII: ['create:precision_mechanism', 'minecraft:phantom_membrane', 'minecraft:blaze_powder'],
    moduleIV: ['minecraft:shulker_shell', 'minecraft:popped_chorus_fruit', 'minecraft:phantom_membrane']
  }
]

function armorId(prof, piece, tier) {
  return `${prof.namespace}:${prof.itemPrefix}_${piece}_${tier}_test`
}

function moduleId(prof, tier) {
  return `kubejs:${prof.id}_module_${tier}`
}

// Material-bearing armor foundation.
//
// The four Silent Gear plate items are already produced by SGear Metalworks
// from the actual molten material. We keep that canonical material component
// on KoshPack profession armor, then derive the physical armor stats from the
// very same Silent Gear material data. Profession/tier still controls the
// model, role abilities and forge slot progression.

const KOSH_ARMOR_MATERIAL_RESULT_EVENT = 'koshpack:profession_armor_material'

var KOSH_ARMOR_DATA_COMPONENTS = Java.loadClass('net.minecraft.core.component.DataComponents')
var KOSH_ARMOR_ITEM_LORE = Java.loadClass('net.minecraft.world.item.component.ItemLore')
var KOSH_ARMOR_ARRAY_LIST = Java.loadClass('java.util.ArrayList')
var KOSH_ARMOR_ITEM_ATTRIBUTE_MODIFIERS = Java.loadClass('net.minecraft.world.item.component.ItemAttributeModifiers')
var KOSH_ARMOR_ATTRIBUTES = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
var KOSH_ARMOR_ATTRIBUTE_MODIFIER = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier')
var KOSH_ARMOR_ATTRIBUTE_OPERATION = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier$Operation')
var KOSH_ARMOR_EQUIPMENT_SLOT = Java.loadClass('net.minecraft.world.entity.EquipmentSlot')
var KOSH_ARMOR_EQUIPMENT_SLOT_GROUP = Java.loadClass('net.minecraft.world.entity.EquipmentSlotGroup')
var KOSH_ARMOR_RESOURCE_LOCATION = Java.loadClass('net.minecraft.resources.ResourceLocation')

var KOSH_SG_COMPOUND_PART_ITEM = Java.loadClass('net.silentchaos512.gear.item.CompoundPartItem')
var KOSH_SG_DATA_COMPONENTS = Java.loadClass('net.silentchaos512.gear.setup.SgDataComponents')
var KOSH_SG_PART_TYPES = Java.loadClass('net.silentchaos512.gear.setup.gear.PartTypes')
var KOSH_SG_GEAR_PROPERTIES = Java.loadClass('net.silentchaos512.gear.setup.gear.GearProperties')
var KOSH_SG_GEAR_TYPES = Java.loadClass('net.silentchaos512.gear.setup.gear.GearTypes')
var KOSH_SG_PROPERTY_KEY = Java.loadClass('net.silentchaos512.gear.api.util.PropertyKey')

const KOSH_ARMOR_DURABILITY_MULTIPLIER = {
  helmet: 11,
  chestplate: 16,
  leggings: 15,
  boots: 13
}

const KOSH_ARMOR_IRON_BASELINE = {
  helmet: { armor: 2, maxDamage: 165 },
  chestplate: { armor: 6, maxDamage: 240 },
  leggings: { armor: 5, maxDamage: 225 },
  boots: { armor: 2, maxDamage: 195 }
}

function koshArmorStackId(stack) {
  if (!stack) return ''
  try { return String(stack.id) } catch (e) {}
  try { return String(stack.getId()) } catch (e) {}
  return ''
}

function koshArmorPlatePiece(id) {
  var keys = Object.keys(ARMOR_BASE_PARTS)
  for (var i = 0; i < keys.length; i++) {
    if (ARMOR_BASE_PARTS[keys[i]] === id) return keys[i]
  }
  return null
}

function koshArmorGearTypeHolder(piece) {
  if (piece === 'helmet') return KOSH_SG_GEAR_TYPES.HELMET
  if (piece === 'chestplate') return KOSH_SG_GEAR_TYPES.CHESTPLATE
  if (piece === 'leggings') return KOSH_SG_GEAR_TYPES.LEGGINGS
  return KOSH_SG_GEAR_TYPES.BOOTS
}

function koshArmorSlot(piece) {
  if (piece === 'helmet') return KOSH_ARMOR_EQUIPMENT_SLOT.HEAD
  if (piece === 'chestplate') return KOSH_ARMOR_EQUIPMENT_SLOT.CHEST
  if (piece === 'leggings') return KOSH_ARMOR_EQUIPMENT_SLOT.LEGS
  return KOSH_ARMOR_EQUIPMENT_SLOT.FEET
}

function koshArmorMaterialProperty(material, propertyHolder, gearTypeHolder) {
  try {
    var key = KOSH_SG_PROPERTY_KEY.of(propertyHolder.get(), gearTypeHolder.get())
    var value = material.getProperty(KOSH_SG_PART_TYPES.MAIN.get(), key)
    var n = Number(value)
    return isFinite(n) ? n : 0
  } catch (e) {
    return 0
  }
}

function koshArmorMaterialStats(plate, piece) {
  var material = null
  try { material = KOSH_SG_COMPOUND_PART_ITEM.getPrimaryMaterial(plate) } catch (e) {}
  if (!material) return null

  var gearType = koshArmorGearTypeHolder(piece)
  var id = ''
  var name = ''
  try { id = String(material.getId()) } catch (e) {}
  try { name = String(material.getSimpleNameWithModifiers().getString()) } catch (e) {}
  if (!name) name = id || 'неизвестный материал'

  var armor = koshArmorMaterialProperty(material, KOSH_SG_GEAR_PROPERTIES.ARMOR, gearType)
  var toughnessRaw = koshArmorMaterialProperty(material, KOSH_SG_GEAR_PROPERTIES.ARMOR_TOUGHNESS, gearType)
  var knockbackRaw = koshArmorMaterialProperty(material, KOSH_SG_GEAR_PROPERTIES.KNOCKBACK_RESISTANCE, gearType)
  var durabilityFactor = koshArmorMaterialProperty(material, KOSH_SG_GEAR_PROPERTIES.ARMOR_DURABILITY, gearType)
  var magicArmor = koshArmorMaterialProperty(material, KOSH_SG_GEAR_PROPERTIES.MAGIC_ARMOR, gearType)

  return {
    id: id,
    name: name,
    armor: Math.max(0, armor),
    toughness: Math.max(0, toughnessRaw / 4),
    knockback: Math.max(0, knockbackRaw / 10),
    magicArmor: Math.max(0, magicArmor),
    maxDamage: Math.max(1, Math.round(durabilityFactor * KOSH_ARMOR_DURABILITY_MULTIPLIER[piece]))
  }
}

function koshArmorCopyUpgradeState(base, result) {
  if (!base) return

  // Workbench upgrades should be as lossless as the old smithing chain:
  // keep enchantments, forge custom_data, names/lore and any other per-stack patch.
  try {
    result.patch(base.getComponentsPatch())
    return
  } catch (e) {}

  // Conservative fallback if a KubeJS/loader build rejects patch().
  try {
    var custom = base.getCustomData()
    if (custom) result.setCustomData(custom.copy())
  } catch (e) {}
  try {
    var lore = base.get(KOSH_ARMOR_DATA_COMPONENTS.LORE)
    if (lore) result.set(KOSH_ARMOR_DATA_COMPONENTS.LORE, lore)
  } catch (e) {}
  try {
    var ench = base.get(KOSH_ARMOR_DATA_COMPONENTS.ENCHANTMENTS)
    if (ench) result.set(KOSH_ARMOR_DATA_COMPONENTS.ENCHANTMENTS, ench)
  } catch (e) {}
  try {
    var customName = base.get(KOSH_ARMOR_DATA_COMPONENTS.CUSTOM_NAME)
    if (customName) result.set(KOSH_ARMOR_DATA_COMPONENTS.CUSTOM_NAME, customName)
  } catch (e) {}
}

function koshArmorApplyAttributes(stack, stats, piece) {
  var slot = koshArmorSlot(piece)
  var group = KOSH_ARMOR_EQUIPMENT_SLOT_GROUP.bySlot(slot)
  var builder = KOSH_ARMOR_ITEM_ATTRIBUTE_MODIFIERS.builder()

  var armorId = KOSH_ARMOR_RESOURCE_LOCATION.fromNamespaceAndPath('koshpack', 'material_armor_' + piece)
  var toughId = KOSH_ARMOR_RESOURCE_LOCATION.fromNamespaceAndPath('koshpack', 'material_toughness_' + piece)
  var knockId = KOSH_ARMOR_RESOURCE_LOCATION.fromNamespaceAndPath('koshpack', 'material_knockback_' + piece)

  builder.add(
    KOSH_ARMOR_ATTRIBUTES.ARMOR,
    new KOSH_ARMOR_ATTRIBUTE_MODIFIER(armorId, stats.armor, KOSH_ARMOR_ATTRIBUTE_OPERATION.ADD_VALUE),
    group
  )

  if (stats.toughness > 0) {
    builder.add(
      KOSH_ARMOR_ATTRIBUTES.ARMOR_TOUGHNESS,
      new KOSH_ARMOR_ATTRIBUTE_MODIFIER(toughId, stats.toughness, KOSH_ARMOR_ATTRIBUTE_OPERATION.ADD_VALUE),
      group
    )
  }

  if (stats.knockback > 0) {
    builder.add(
      KOSH_ARMOR_ATTRIBUTES.KNOCKBACK_RESISTANCE,
      new KOSH_ARMOR_ATTRIBUTE_MODIFIER(knockId, stats.knockback, KOSH_ARMOR_ATTRIBUTE_OPERATION.ADD_VALUE),
      group
    )
  }

  stack.set(KOSH_ARMOR_DATA_COMPONENTS.ATTRIBUTE_MODIFIERS, builder.build())
  stack.set(KOSH_ARMOR_DATA_COMPONENTS.MAX_DAMAGE, stats.maxDamage)

  // Preserve wear from the previous tier, but never produce an invalid damage value
  // if the player deliberately switches to a less durable material.
  var damage = 0
  try { damage = Number(stack.getDamageValue()) } catch (e) {}
  if (!isFinite(damage) || damage < 0) damage = 0
  stack.set(KOSH_ARMOR_DATA_COMPONENTS.DAMAGE, Math.min(Math.floor(damage), Math.max(0, stats.maxDamage - 1)))
}

function koshArmorFmt(value) {
  var rounded = Math.round(Number(value) * 10) / 10
  if (Math.abs(rounded - Math.round(rounded)) < 0.001) return String(Math.round(rounded))
  return String(rounded)
}

function koshArmorMaterialLore(stack, stats, piece) {
  var lines = new KOSH_ARMOR_ARRAY_LIST()

  // Keep existing lore (including forge slots), replacing only our managed material lines.
  try {
    var oldLore = stack.get(KOSH_ARMOR_DATA_COMPONENTS.LORE)
    if (oldLore) {
      var iterator = oldLore.lines().iterator()
      while (iterator.hasNext()) {
        var line = iterator.next()
        var plain = ''
        try { plain = String(line.getString()) } catch (e) {}
        if (
          plain.indexOf('◆ Материал основы: ') !== 0 &&
          plain.indexOf('Физика основы: ') !== 0 &&
          plain.indexOf('Плюсы материала: ') !== 0 &&
          plain.indexOf('Минусы материала: ') !== 0
        ) {
          lines.add(line)
        }
      }
    }
  } catch (e) {}

  lines.add(Text.aqua('◆ Материал основы: ' + stats.name))

  var physical = 'Физика основы: ' + koshArmorFmt(stats.armor) + ' защиты'
  if (stats.toughness > 0) physical += ' • ' + koshArmorFmt(stats.toughness) + ' стойкости'
  if (stats.knockback > 0) physical += ' • ' + koshArmorFmt(stats.knockback) + ' сопр. отбрасыванию'
  physical += ' • ' + stats.maxDamage + ' прочности'
  lines.add(Text.gray(physical))

  var baseline = KOSH_ARMOR_IRON_BASELINE[piece]
  var positives = []
  var negatives = []
  var armorDelta = stats.armor - baseline.armor
  var durabilityPct = Math.round((stats.maxDamage / baseline.maxDamage - 1) * 100)

  if (armorDelta > 0.05) positives.push('защита +' + koshArmorFmt(armorDelta))
  if (armorDelta < -0.05) negatives.push('защита ' + koshArmorFmt(armorDelta))
  if (stats.toughness > 0.01) positives.push('стойкость +' + koshArmorFmt(stats.toughness))
  if (stats.knockback > 0.001) positives.push('отбрасывание +' + koshArmorFmt(stats.knockback))
  if (durabilityPct > 0) positives.push('прочность +' + durabilityPct + '%')
  if (durabilityPct < 0) negatives.push('прочность ' + durabilityPct + '%')

  if (positives.length > 0) lines.add(Text.green('Плюсы материала: ' + positives.join(', ')))
  if (negatives.length > 0) lines.add(Text.red('Минусы материала: ' + negatives.join(', ')))
  if (positives.length === 0 && negatives.length === 0) lines.add(Text.darkGray('Материал по физике близок к железной основе.'))

  stack.set(KOSH_ARMOR_DATA_COMPONENTS.LORE, new KOSH_ARMOR_ITEM_LORE(lines))
}

function koshArmorWriteMaterialData(stack, stats, piece) {
  var tag = null
  try { tag = stack.getCustomData() } catch (e) {}
  if (!tag) return

  tag.putInt('kosh_armor_material_schema', 1)
  tag.putString('kosh_armor_material_id', stats.id)
  tag.putString('kosh_armor_material_name', stats.name)
  tag.putString('kosh_armor_material_piece', piece)
  tag.putFloat('kosh_armor_material_armor', stats.armor)
  tag.putFloat('kosh_armor_material_toughness', stats.toughness)
  tag.putFloat('kosh_armor_material_knockback', stats.knockback)
  tag.putFloat('kosh_armor_material_magic_armor', stats.magicArmor)
  tag.putInt('kosh_armor_material_max_damage', stats.maxDamage)
  stack.setCustomData(tag)
}

ServerEvents.recipes(event => {
  PROFESSIONS.forEach(prof => {
    // Remove direct/legacy recipes for all 272 visual armor items first.
    ;['i', 'ii', 'iii', 'iv'].forEach(tier => {
      ARMOR_PIECES.forEach(piece => event.remove({ output: armorId(prof, piece.id, tier) }))
    })

    // Profession module chain remains the technology/profession gate.
    event.shapeless(moduleId(prof, 'i'), prof.moduleI)
      .id('kubejs:armor/modules/' + prof.id + '_i')

    event.shapeless(moduleId(prof, 'ii'), [moduleId(prof, 'i')].concat(prof.moduleII))
      .id('kubejs:armor/modules/' + prof.id + '_ii')

    event.shapeless(moduleId(prof, 'iii'), [moduleId(prof, 'ii')].concat(prof.moduleIII))
      .id('kubejs:armor/modules/' + prof.id + '_iii')

    event.shapeless(moduleId(prof, 'iv'), [moduleId(prof, 'iii')].concat(prof.moduleIV))
      .id('kubejs:armor/modules/' + prof.id + '_iv')

    // Tier I is now a real Foundry-backed assembly too:
    // profession module + material-bearing cast plate + cheap profession shell materials.
    ARMOR_PIECES.forEach(piece => {
      event.shapeless(
        armorId(prof, piece.id, 'i'),
        [moduleId(prof, 'i'), ARMOR_BASE_PARTS[piece.id]].concat(piece.tier1Extra)
      )
        .modifyResult(KOSH_ARMOR_MATERIAL_RESULT_EVENT)
        .id('kubejs:armor/assembly/' + prof.id + '/' + piece.id + '_i')
    })

    // Tiers II-IV stay strictly sequential, but are assembled on the workbench.
    // A newly cast plate is mandatory at every step and can intentionally change
    // the armor's material without changing its profession or visual tier.
    ARMOR_TIER_CHAIN.forEach(tier => {
      ARMOR_PIECES.forEach(piece => {
        event.shapeless(
          armorId(prof, piece.id, tier.id),
          [
            armorId(prof, piece.id, tier.prev),
            moduleId(prof, tier.id),
            ARMOR_BASE_PARTS[piece.id]
          ]
        )
          .modifyResult(KOSH_ARMOR_MATERIAL_RESULT_EVENT)
          .id('kubejs:armor/upgrade/' + prof.id + '/' + piece.id + '_' + tier.id)
      })
    })
  })
})

ServerEvents.modifyRecipeResult(KOSH_ARMOR_MATERIAL_RESULT_EVENT, event => {
  var plate = null
  var base = null
  var piece = null

  var stacks = event.grid.findAll()
  var iterator = stacks.iterator()
  while (iterator.hasNext()) {
    var stack = iterator.next()
    var id = koshArmorStackId(stack)
    var platePiece = koshArmorPlatePiece(id)

    if (platePiece) {
      plate = stack
      piece = platePiece
    } else if (id.indexOf('koshpack') === 0 && id.indexOf(':') > 0) {
      // All current profession armor namespaces begin with koshpack*.
      // KubeJS profession modules are in the kubejs namespace, so they cannot match.
      base = stack
    }
  }

  if (!plate || !piece) return

  var result = event.item
  if (base) koshArmorCopyUpgradeState(base, result)

  // Preserve the canonical Silent Gear material list itself on the final armor.
  // This is the source of truth for future refinements, not just a copied text ID.
  try {
    var materialList = plate.get(KOSH_SG_DATA_COMPONENTS.MATERIAL_LIST.get())
    if (materialList) result.set(KOSH_SG_DATA_COMPONENTS.MATERIAL_LIST.get(), materialList)
  } catch (e) {}

  var stats = koshArmorMaterialStats(plate, piece)
  if (!stats) return

  koshArmorApplyAttributes(result, stats, piece)
  koshArmorWriteMaterialData(result, stats, piece)
  koshArmorMaterialLore(result, stats, piece)

  event.exit(result)
})
