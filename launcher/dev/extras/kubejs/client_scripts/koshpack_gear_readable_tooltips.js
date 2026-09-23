// KoshPack readable live tooltips for Silent Gear weapons/tools.
//
// Silent Gear rebuilds parts of its tooltip after crafting, so player-facing
// material information is rendered dynamically from the final live ItemStack.
// This keeps the summary correct after material replacement, damage and forge work.

const KOSH_GEAR_TOOLTIP_ROWS = [
  ['silentgear:sword', 'weapon'],
  ['silentgear:katana', 'weapon'],
  ['silentgear:machete', 'weapon'],
  ['silentgear:knife', 'weapon'],
  ['silentgear:dagger', 'weapon'],
  ['silentgear:spear', 'weapon'],
  ['silentgear:trident', 'weapon'],
  ['silentgear:mace', 'weapon'],
  ['silentgear:shield', 'weapon'],
  ['silentgear:bow', 'weapon'],
  ['silentgear:crossbow', 'weapon'],
  ['silentgear:slingshot', 'weapon'],

  ['silentgear:pickaxe', 'tool'],
  ['silentgear:shovel', 'tool'],
  ['silentgear:axe', 'tool'],
  ['silentgear:paxel', 'tool'],
  ['silentgear:hammer', 'tool'],
  ['silentgear:excavator', 'tool'],
  ['silentgear:saw', 'tool'],
  ['silentgear:prospector_hammer', 'tool'],
  ['silentgear:hoe', 'tool'],
  ['silentgear:mattock', 'tool'],
  ['silentgear:sickle', 'tool'],
  ['silentgear:shears', 'tool'],
  ['silentgear:fishing_rod', 'tool']
]

var KOSH_GEAR_TOOLTIP_KIND = {}
KOSH_GEAR_TOOLTIP_ROWS.forEach(function(row) {
  KOSH_GEAR_TOOLTIP_KIND[row[0]] = row[1]
})

const KOSH_GEAR_SHOW_HARVEST_TIER = {
  'silentgear:pickaxe': true,
  'silentgear:paxel': true,
  'silentgear:hammer': true,
  'silentgear:excavator': true,
  'silentgear:prospector_hammer': true
}

const KOSH_GEAR_HARVEST_NAMES = {
  zero: 'дерево',
  wood: 'дерево',
  gold: 'золото',
  stone: 'камень',
  copper: 'медь',
  iron: 'железо',
  diamond: 'алмаз',
  netherite: 'незерит'
}

var KOSH_TIP_GEAR_DATA = Java.loadClass('net.silentchaos512.gear.util.GearData')
var KOSH_TIP_PART_INSTANCE = Java.loadClass('net.silentchaos512.gear.gear.part.PartInstance')
var KOSH_TIP_COMPOUND_PART = Java.loadClass('net.silentchaos512.gear.item.CompoundPartItem')
var KOSH_TIP_MATERIAL_INSTANCE = Java.loadClass('net.silentchaos512.gear.gear.material.MaterialInstance')
var KOSH_TIP_BUILTIN_MATERIALS = Java.loadClass('net.silentchaos512.gear.core.BuiltinMaterials')
var KOSH_TIP_PROPERTIES = Java.loadClass('net.silentchaos512.gear.setup.gear.GearProperties')
var KOSH_TIP_PART_TYPES = Java.loadClass('net.silentchaos512.gear.setup.gear.PartTypes')
var KOSH_TIP_PROPERTY_KEY = Java.loadClass('net.silentchaos512.gear.api.util.PropertyKey')
var KOSH_TIP_ARRAY_LIST = Java.loadClass('java.util.ArrayList')

function koshTipId(stack) {
  if (!stack) return ''
  try { return String(stack.id) } catch (e) {}
  try { return String(stack.getId()) } catch (e) {}
  return ''
}

function koshTipFmt(value) {
  var n = Number(value)
  if (!isFinite(n)) return '0'
  var rounded = Math.round(n * 100) / 100
  if (Math.abs(rounded - Math.round(rounded)) < 0.0001) return String(Math.round(rounded))
  return rounded.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function koshTipNumber(stack, property) {
  try {
    return Number(KOSH_TIP_GEAR_DATA.getProperties(stack).getNumber(property))
  } catch (e) {}
  return 0
}

function koshTipHarvestTier(stack) {
  if (!KOSH_GEAR_SHOW_HARVEST_TIER[koshTipId(stack)]) return null

  try {
    var value = KOSH_TIP_GEAR_DATA.getProperties(stack).get(KOSH_TIP_PROPERTIES.HARVEST_TIER)
    if (!value) return null

    var tier = value.value()
    if (!tier) return null

    var name = String(tier.name())
    var hint = ''
    try {
      var optionalHint = tier.levelHint()
      if (optionalHint && optionalHint.isPresent()) hint = String(optionalHint.get())
    } catch (e) {}

    var level = Number(hint)
    var reachLabel = ''

    // Do not hardcode vanilla ores here: KoshPack contains modded stone/ore tags.
    // The harvest tier is the authoritative rule; any modded blocks added to the
    // relevant tags automatically follow it.
    if (isFinite(level)) {
      if (level < 1) reachLabel = 'базового тира'
      else if (level < 1.5) reachLabel = 'каменного тира'
      else if (level < 2) reachLabel = 'медного тира'
      else if (level < 3) reachLabel = 'железного тира'
      else if (level < 4) reachLabel = 'алмазного тира'
      else reachLabel = 'незеритового тира'
    }

    return {
      name: KOSH_GEAR_HARVEST_NAMES[name] || name,
      hint: hint,
      reachLabel: reachLabel
    }
  } catch (e) {}

  return null
}

function koshTipMainPart(stack) {
  try {
    var construction = KOSH_TIP_GEAR_DATA.getConstruction(stack)
    var primary = construction.getPrimaryPart()
    if (!primary) return null
    var partStack = primary.getItem()
    if (!partStack || partStack.empty) return null
    return partStack
  } catch (e) {}
  return null
}

function koshTipMaterialName(partStack) {
  if (!partStack) return 'неизвестный материал'
  try {
    var material = KOSH_TIP_COMPOUND_PART.getPrimaryMaterial(partStack)
    if (!material) return 'неизвестный материал'
    try { return String(material.getSimpleName().getString()) } catch (e) {}
    try { return String(material.getId()) } catch (e) {}
  } catch (e) {}
  return 'неизвестный материал'
}

function koshTipIronReference(stack, partStack) {
  try {
    var partItem = partStack.getItem()
    var ironMaterial = KOSH_TIP_MATERIAL_INSTANCE.of(KOSH_TIP_BUILTIN_MATERIALS.IRON.getMaterial())
    var ironPartStack = partItem.create(ironMaterial)
    var ironPart = KOSH_TIP_PART_INSTANCE.from(ironPartStack)
    if (!ironPart) return null

    var reference = stack.copy()
    reference.count = 1
    KOSH_TIP_GEAR_DATA.addOrReplacePart(reference, ironPart)
    try { ironPart.onAddToGear(reference) } catch (e) {}
    KOSH_TIP_GEAR_DATA.recalculateGearData(reference, null)
    return reference
  } catch (e) {}
  return null
}

function koshTipState(stack) {
  var maxDamage = 0
  var damage = 0
  try { maxDamage = Number(stack.getMaxDamage()) } catch (e) {}
  try { damage = Number(stack.getDamageValue()) } catch (e) {}

  if (!isFinite(maxDamage) || maxDamage <= 0) return null
  if (!isFinite(damage) || damage < 0) damage = 0

  var left = Math.max(0, maxDamage - damage)
  return {
    left: Math.round(left),
    max: Math.round(maxDamage),
    percent: Math.max(0, Math.min(100, Math.round(left / maxDamage * 100)))
  }
}

function koshTipPhysics(stack, kind) {
  var parts = []

  var attack = koshTipNumber(stack, KOSH_TIP_PROPERTIES.ATTACK_DAMAGE)
  var attackSpeed = koshTipNumber(stack, KOSH_TIP_PROPERTIES.ATTACK_SPEED)
  var harvest = koshTipNumber(stack, KOSH_TIP_PROPERTIES.HARVEST_SPEED)
  var attackReach = koshTipNumber(stack, KOSH_TIP_PROPERTIES.ATTACK_REACH)
  var blockReach = koshTipNumber(stack, KOSH_TIP_PROPERTIES.BLOCK_REACH)
  var rangedDamage = koshTipNumber(stack, KOSH_TIP_PROPERTIES.RANGED_DAMAGE)
  var drawSpeed = koshTipNumber(stack, KOSH_TIP_PROPERTIES.DRAW_SPEED)
  var projectileSpeed = koshTipNumber(stack, KOSH_TIP_PROPERTIES.PROJECTILE_SPEED)

  if (kind === 'tool') {
    if (harvest > 0.01) parts.push(koshTipFmt(harvest) + ' скорость добычи')
    if (attack > 0.01) parts.push(koshTipFmt(attack + 1) + ' урона')
    if (attackSpeed !== 0) parts.push(koshTipFmt(attackSpeed) + ' скорость атаки')
    if (blockReach !== 0) parts.push(koshTipFmt(blockReach) + ' дальность блоков')
  } else {
    if (attack > 0.01) parts.push(koshTipFmt(attack + 1) + ' урона')
    if (attackSpeed !== 0) parts.push(koshTipFmt(attackSpeed) + ' скорость атаки')
    if (attackReach !== 0) parts.push(koshTipFmt(attackReach) + ' дальность атаки')
    if (rangedDamage > 0.01) parts.push('×' + koshTipFmt(rangedDamage) + ' дальний урон')
    if (drawSpeed !== 0) parts.push('×' + koshTipFmt(drawSpeed) + ' натяжение')
    if (projectileSpeed > 1.001) parts.push('×' + koshTipFmt(projectileSpeed) + ' скорость снаряда')
  }

  return parts
}

function koshTipMaterialProperty(material, partInstance, propertySupplier) {
  if (!material || !partInstance) return NaN
  try {
    var property = propertySupplier.get()
    var key = KOSH_TIP_PROPERTY_KEY.of(property, partInstance.getGearType())
    return Number(material.getProperty(partInstance.getType(), key))
  } catch (e) {}
  return NaN
}

function koshTipMaterialDiff(mainPartStack) {
  var positives = []
  var negatives = []
  var compared = false

  var partInstance = null
  var currentMaterial = null
  var ironMaterial = null

  try { partInstance = KOSH_TIP_PART_INSTANCE.from(mainPartStack) } catch (e) {}
  if (!partInstance) return { positives: positives, negatives: negatives, compared: false }

  try { currentMaterial = partInstance.getPrimaryMaterial() } catch (e) {}
  try { ironMaterial = KOSH_TIP_MATERIAL_INSTANCE.of(KOSH_TIP_BUILTIN_MATERIALS.IRON.getMaterial()) } catch (e) {}
  if (!currentMaterial || !ironMaterial) return { positives: positives, negatives: negatives, compared: false }

  function compare(label, propertySupplier, threshold) {
    var actual = koshTipMaterialProperty(currentMaterial, partInstance, propertySupplier)
    var iron = koshTipMaterialProperty(ironMaterial, partInstance, propertySupplier)
    if (!isFinite(actual) || !isFinite(iron)) return

    compared = true
    var delta = actual - iron
    if (delta > threshold) positives.push(label + ' +' + koshTipFmt(delta))
    if (delta < -threshold) negatives.push(label + ' ' + koshTipFmt(delta))
  }

  compare('урон', KOSH_TIP_PROPERTIES.ATTACK_DAMAGE, 0.01)
  compare('скорость атаки', KOSH_TIP_PROPERTIES.ATTACK_SPEED, 0.01)
  compare('скорость добычи', KOSH_TIP_PROPERTIES.HARVEST_SPEED, 0.05)

  var actualDurability = koshTipMaterialProperty(currentMaterial, partInstance, KOSH_TIP_PROPERTIES.DURABILITY)
  var ironDurability = koshTipMaterialProperty(ironMaterial, partInstance, KOSH_TIP_PROPERTIES.DURABILITY)

  if (isFinite(actualDurability) && isFinite(ironDurability) && ironDurability > 0) {
    compared = true
    var pct = Math.round((actualDurability / ironDurability - 1) * 100)
    if (pct > 0) positives.push('прочность +' + pct + '%')
    if (pct < 0) negatives.push('прочность ' + pct + '%')
  }

  return { positives: positives, negatives: negatives, compared: compared }
}

function koshTipRemoveOldManagedLines(lines) {
  var iterator = lines.iterator()
  while (iterator.hasNext()) {
    var line = iterator.next()
    var plain = ''
    try { plain = String(line.getString()) } catch (e) {}

    if (
      plain.indexOf('◆ Рабочая часть: ') === 0 ||
      plain.indexOf('◆ Материал рабочей части: ') === 0 ||
      plain.indexOf('Итоговая физика: ') === 0 ||
      plain.indexOf('Характеристики: ') === 0 ||
      plain.indexOf('Уровень добычи: ') === 0 ||
      plain.indexOf('Состояние: ') === 0 ||
      plain.indexOf('Плюсы материала: ') === 0 ||
      plain.indexOf('Минусы материала: ') === 0 ||
      plain.indexOf('Материал по физике близок к железу.') === 0
    ) {
      iterator.remove()
    }
  }
}

function koshTipInsertIndex(lines) {
  for (var i = 0; i < lines.size(); i++) {
    var plain = ''
    try { plain = String(lines.get(i).getString()) } catch (e) {}
    if (
      plain.indexOf('Traits:') === 0 ||
      plain.indexOf('Properties') === 0 ||
      plain.indexOf('Конструкция') === 0 ||
      plain.indexOf('Заточки: [') === 0
    ) {
      return i
    }
  }
  return lines.size()
}

function koshTipBuildBlock(stack, kind) {
  var block = new KOSH_TIP_ARRAY_LIST()
  var mainPart = koshTipMainPart(stack)
  if (!mainPart) return block

  block.add(Text.aqua('◆ Материал рабочей части: ' + koshTipMaterialName(mainPart)))

  var physics = koshTipPhysics(stack, kind)
  if (physics.length > 0) {
    block.add(Text.gray('Характеристики: ' + physics.join(' • ')))
  }

  var harvestTier = koshTipHarvestTier(stack)
  if (harvestTier) {
    var tierText = 'Уровень добычи: ' + harvestTier.name
    if (harvestTier.hint) tierText += ' ' + harvestTier.hint
    if (harvestTier.reachLabel) tierText += ' • Берёт: всё до ' + harvestTier.reachLabel
    block.add(Text.gold(tierText))
  }

  var state = koshTipState(stack)
  if (state) {
    if (state.percent >= 70) {
      block.add(Text.green('Состояние: ' + state.left + ' / ' + state.max + ' • ' + state.percent + '%'))
    } else if (state.percent >= 35) {
      block.add(Text.yellow('Состояние: ' + state.left + ' / ' + state.max + ' • ' + state.percent + '%'))
    } else {
      block.add(Text.red('Состояние: ' + state.left + ' / ' + state.max + ' • ' + state.percent + '%'))
    }
  }

  var diff = koshTipMaterialDiff(mainPart)

  if (diff.positives.length > 0) {
    block.add(Text.green('Плюсы материала: ' + diff.positives.join(', ')))
  }
  if (diff.negatives.length > 0) {
    block.add(Text.red('Минусы материала: ' + diff.negatives.join(', ')))
  }
  if (diff.compared && diff.positives.length === 0 && diff.negatives.length === 0) {
    block.add(Text.darkGray('Материал по физике близок к железу.'))
  }

  return block
}

ItemEvents.modifyTooltips(function(event) {
  KOSH_GEAR_TOOLTIP_ROWS.forEach(function(row) {
    var itemId = row[0]
    var dynamicId = 'koshpack_gear_' + itemId.replace(':', '_')
    event.modify(itemId, function(builder) {
      builder.dynamic(dynamicId)
    })
  })
})

KOSH_GEAR_TOOLTIP_ROWS.forEach(function(row) {
  var itemId = row[0]
  var kind = row[1]
  var dynamicId = 'koshpack_gear_' + itemId.replace(':', '_')

  ItemEvents.dynamicTooltips(dynamicId, function(event) {
    try {
      koshTipRemoveOldManagedLines(event.lines)

      var block = koshTipBuildBlock(event.item, kind)
      if (block.isEmpty()) return

      var index = koshTipInsertIndex(event.lines)
      event.lines.addAll(index, block)
    } catch (e) {
      // A tooltip must never break item rendering.
    }
  })
})
