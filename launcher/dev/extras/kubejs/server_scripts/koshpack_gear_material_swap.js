// KoshPack weapon/tool material replacement v1.
//
// Silent Gear weapons and tools already carry a real construction graph.
// This layer makes the main working part replaceable after assembly:
//   finished gear + newly cast matching MAIN part -> same gear with new material.
//
// Guarantees:
// - forge treatments/custom data stay on the same stack identity;
// - enchantments/name/lore are preserved;
// - damage is transferred by percentage, so a stronger material is not a free repair;
// - Silent Gear recalculates its native stats/model from the new part;
// - raw material pros/cons are shown relative to an iron working part;
// - frame-integrity fields are initialized now for the later finite-repair lifecycle.

const KOSH_GEAR_MATERIAL_RESULT_EVENT = 'koshpack:gear_material_swap'

const KOSH_GEAR_SWAP_TYPES = [
  { gear: 'silentgear:sword', part: 'silentgear:sword_blade', kind: 'weapon' },
  { gear: 'silentgear:katana', part: 'silentgear:katana_blade', kind: 'weapon' },
  { gear: 'silentgear:machete', part: 'silentgear:machete_blade', kind: 'weapon' },
  { gear: 'silentgear:knife', part: 'silentgear:knife_blade', kind: 'weapon' },
  { gear: 'silentgear:dagger', part: 'silentgear:dagger_blade', kind: 'weapon' },
  { gear: 'silentgear:spear', part: 'silentgear:spear_tip', kind: 'weapon' },
  { gear: 'silentgear:trident', part: 'silentgear:trident_prongs', kind: 'weapon' },
  { gear: 'silentgear:mace', part: 'silentgear:mace_core', kind: 'weapon' },
  { gear: 'silentgear:shield', part: 'silentgear:shield_plate', kind: 'weapon' },
  { gear: 'silentgear:bow', part: 'silentgear:bow_limbs', kind: 'weapon' },
  { gear: 'silentgear:crossbow', part: 'silentgear:crossbow_limbs', kind: 'weapon' },
  { gear: 'silentgear:slingshot', part: 'silentgear:slingshot_limbs', kind: 'weapon' },

  { gear: 'silentgear:pickaxe', part: 'silentgear:pickaxe_head', kind: 'tool' },
  { gear: 'silentgear:shovel', part: 'silentgear:shovel_head', kind: 'tool' },
  { gear: 'silentgear:axe', part: 'silentgear:axe_head', kind: 'tool' },
  { gear: 'silentgear:paxel', part: 'silentgear:paxel_head', kind: 'tool' },
  { gear: 'silentgear:hammer', part: 'silentgear:hammer_head', kind: 'tool' },
  { gear: 'silentgear:excavator', part: 'silentgear:excavator_head', kind: 'tool' },
  { gear: 'silentgear:saw', part: 'silentgear:saw_blade', kind: 'tool' },
  { gear: 'silentgear:prospector_hammer', part: 'silentgear:prospector_hammer_head', kind: 'tool' },
  { gear: 'silentgear:hoe', part: 'silentgear:hoe_head', kind: 'tool' },
  { gear: 'silentgear:mattock', part: 'silentgear:mattock_head', kind: 'tool' },
  { gear: 'silentgear:sickle', part: 'silentgear:sickle_blade', kind: 'tool' },
  { gear: 'silentgear:shears', part: 'silentgear:shear_blades', kind: 'tool' },
  { gear: 'silentgear:fishing_rod', part: 'silentgear:fishing_reel_and_hook', kind: 'tool' }
]

var KOSH_GEAR_BY_GEAR = {}
var KOSH_GEAR_BY_PART = {}
KOSH_GEAR_SWAP_TYPES.forEach(function(row) {
  KOSH_GEAR_BY_GEAR[row.gear] = row
  KOSH_GEAR_BY_PART[row.part] = row
})

var KOSH_GEAR_DATA_COMPONENTS = Java.loadClass('net.minecraft.core.component.DataComponents')
var KOSH_GEAR_ITEM_LORE = Java.loadClass('net.minecraft.world.item.component.ItemLore')
var KOSH_GEAR_ARRAY_LIST = Java.loadClass('java.util.ArrayList')

var KOSH_GEAR_DATA = Java.loadClass('net.silentchaos512.gear.util.GearData')
var KOSH_GEAR_PART_INSTANCE = Java.loadClass('net.silentchaos512.gear.gear.part.PartInstance')
var KOSH_GEAR_COMPOUND_PART_ITEM = Java.loadClass('net.silentchaos512.gear.item.CompoundPartItem')
var KOSH_GEAR_MATERIAL_INSTANCE = Java.loadClass('net.silentchaos512.gear.gear.material.MaterialInstance')
var KOSH_GEAR_BUILTIN_MATERIALS = Java.loadClass('net.silentchaos512.gear.core.BuiltinMaterials')
var KOSH_GEAR_PROPERTIES = Java.loadClass('net.silentchaos512.gear.setup.gear.GearProperties')

function koshGearStackId(stack) {
  if (!stack) return ''
  try { return String(stack.id) } catch (e) {}
  try { return String(stack.getId()) } catch (e) {}
  return ''
}

function koshGearWearFraction(stack) {
  if (!stack) return 0

  var maxDamage = 0
  var damage = 0
  try { maxDamage = Number(stack.getMaxDamage()) } catch (e) {}
  try { damage = Number(stack.getDamageValue()) } catch (e) {}

  if (!isFinite(maxDamage) || maxDamage <= 0 || !isFinite(damage) || damage <= 0) return 0
  return Math.max(0, Math.min(1, damage / maxDamage))
}

function koshGearForgeSnapshot(stack) {
  var out = { version: '', loreSig: '', slots: [] }
  if (!stack) return out

  var tag = null
  try { tag = stack.getCustomData() } catch (e) {}
  if (!tag) return out

  try { out.version = String(tag.getString('kosh_forge_version').orElse('')) } catch (e) {
    try { out.version = String(tag.getString('kosh_forge_version')) } catch (_e) {}
  }
  try { out.loreSig = String(tag.getString('kosh_forge_lore_sig').orElse('')) } catch (e) {
    try { out.loreSig = String(tag.getString('kosh_forge_lore_sig')) } catch (_e) {}
  }

  for (var i = 0; i < 3; i++) {
    var id = ''
    var level = 0
    try { id = String(tag.getString('kosh_forge_slot_' + i + '_id').orElse('')) } catch (e) {
      try { id = String(tag.getString('kosh_forge_slot_' + i + '_id')) } catch (_e) {}
    }
    try { level = Number(tag.getInt('kosh_forge_slot_' + i + '_level').orElse(0)) } catch (e) {
      try { level = Number(tag.getInt('kosh_forge_slot_' + i + '_level')) } catch (_e) {}
    }
    out.slots.push({ id: id, level: level })
  }

  return out
}

function koshGearRestoreForgeSnapshot(stack, snapshot) {
  if (!stack || !snapshot) return

  var tag = null
  try { tag = stack.getCustomData() } catch (e) {}
  if (!tag) return

  if (snapshot.version) tag.putString('kosh_forge_version', snapshot.version)
  if (snapshot.loreSig) tag.putString('kosh_forge_lore_sig', snapshot.loreSig)

  for (var i = 0; i < 3; i++) {
    var slot = snapshot.slots && snapshot.slots[i] ? snapshot.slots[i] : null
    if (slot && slot.id && slot.level > 0) {
      tag.putString('kosh_forge_slot_' + i + '_id', slot.id)
      tag.putInt('kosh_forge_slot_' + i + '_level', slot.level)
    } else {
      try { tag.remove('kosh_forge_slot_' + i + '_id') } catch (e) {}
      try { tag.remove('kosh_forge_slot_' + i + '_level') } catch (e) {}
    }
  }

  stack.setCustomData(tag)
}

function koshGearFmt(value) {
  var n = Number(value)
  if (!isFinite(n)) return '0'
  var rounded = Math.round(n * 100) / 100
  if (Math.abs(rounded - Math.round(rounded)) < 0.0001) return String(Math.round(rounded))
  return rounded.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function koshGearMaterial(partStack) {
  try { return KOSH_GEAR_COMPOUND_PART_ITEM.getPrimaryMaterial(partStack) } catch (e) {}
  return null
}

function koshGearMaterialName(partStack) {
  var material = koshGearMaterial(partStack)
  if (!material) return 'неизвестный материал'
  try { return String(material.getSimpleName().getString()) } catch (e) {}
  try { return String(material.getId()) } catch (e) {}
  return 'неизвестный материал'
}

function koshGearMaterialId(partStack) {
  var material = koshGearMaterial(partStack)
  if (!material) return ''
  try { return String(material.getId()) } catch (e) {}
  return ''
}

function koshGearKind(stack) {
  var row = KOSH_GEAR_BY_GEAR[koshGearStackId(stack)]
  return row ? row.kind : ''
}

function koshGearDurabilitySummary(stack) {
  var maxDamage = 0
  var damage = 0

  try { maxDamage = Number(stack.getMaxDamage()) } catch (e) {}
  try { damage = Number(stack.getDamageValue()) } catch (e) {}

  if (!isFinite(maxDamage) || maxDamage <= 0) return null
  if (!isFinite(damage) || damage < 0) damage = 0

  var left = Math.max(0, maxDamage - damage)
  var pct = Math.round((left / maxDamage) * 100)
  return {
    left: Math.round(left),
    max: Math.round(maxDamage),
    percent: Math.max(0, Math.min(100, pct))
  }
}

function koshGearPhysicsText(stack) {
  var kind = koshGearKind(stack)
  var parts = []

  var attack = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.ATTACK_DAMAGE)
  var attackSpeed = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.ATTACK_SPEED)
  var harvest = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.HARVEST_SPEED)
  var attackReach = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.ATTACK_REACH)
  var blockReach = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.BLOCK_REACH)
  var ranged = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.RANGED_DAMAGE)
  var drawSpeed = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.DRAW_SPEED)
  var projectileSpeed = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.PROJECTILE_SPEED)

  if (kind === 'tool') {
    if (harvest > 0.01) parts.push(koshGearFmt(harvest) + ' скорость добычи')
    if (attack > 0.01) parts.push(koshGearFmt(attack) + ' урона')
    if (attackSpeed !== 0) parts.push(koshGearFmt(attackSpeed) + ' скорость атаки')
    if (blockReach !== 0) parts.push(koshGearFmt(blockReach) + ' дальность блоков')
  } else {
    if (attack > 0.01) parts.push(koshGearFmt(attack) + ' урона')
    if (attackSpeed !== 0) parts.push(koshGearFmt(attackSpeed) + ' скорость атаки')
    if (attackReach !== 0) parts.push(koshGearFmt(attackReach) + ' дальность атаки')
    if (ranged > 0.01) parts.push('×' + koshGearFmt(ranged) + ' дальний урон')
    if (drawSpeed !== 0) parts.push('×' + koshGearFmt(drawSpeed) + ' натяжение')
    if (projectileSpeed > 1.001) parts.push('×' + koshGearFmt(projectileSpeed) + ' скорость снаряда')
  }

  return parts
}

function koshGearNumber(stack, property) {
  try {
    var props = KOSH_GEAR_DATA.getProperties(stack)
    return Number(props.getNumber(property))
  } catch (e) {}
  return 0
}

function koshGearIronReference(base, partStack) {
  try {
    var item = partStack.getItem()
    var ironMaterial = KOSH_GEAR_MATERIAL_INSTANCE.of(KOSH_GEAR_BUILTIN_MATERIALS.IRON.getMaterial())
    var ironPartStack = item.create(ironMaterial)
    var ironPart = KOSH_GEAR_PART_INSTANCE.from(ironPartStack)
    if (!ironPart) return null

    var reference = base.copy()
    reference.count = 1
    KOSH_GEAR_DATA.addOrReplacePart(reference, ironPart)
    try { ironPart.onAddToGear(reference) } catch (e) {}
    KOSH_GEAR_DATA.recalculateGearData(reference, null)
    return reference
  } catch (e) {
    return null
  }
}

function koshGearStampFrame(stack, partStack) {
  var tag = null
  try { tag = stack.getCustomData() } catch (e) {}
  if (!tag) return

  var hasSchema = false
  try { hasSchema = tag.contains('kosh_gear_frame_schema') } catch (e) {}

  if (!hasSchema) {
    tag.putInt('kosh_gear_frame_schema', 1)
    tag.putInt('kosh_gear_frame_integrity_permille', 1000)
    tag.putInt('kosh_gear_repair_count', 0)
  }

  tag.putString('kosh_gear_working_material_id', koshGearMaterialId(partStack))
  tag.putString('kosh_gear_working_material_name', koshGearMaterialName(partStack))
  stack.setCustomData(tag)
}

function koshGearMaterialLore(stack, partStack, ironReference) {
  var lines = new KOSH_GEAR_ARRAY_LIST()

  try {
    var oldLore = stack.get(KOSH_GEAR_DATA_COMPONENTS.LORE)
    if (oldLore) {
      var iterator = oldLore.lines().iterator()
      while (iterator.hasNext()) {
        var line = iterator.next()
        var plain = ''
        try { plain = String(line.getString()) } catch (e) {}

        if (
          plain.indexOf('◆ Рабочая часть: ') !== 0 &&
          plain.indexOf('◆ Материал рабочей части: ') !== 0 &&
          plain.indexOf('Итоговая физика: ') !== 0 &&
          plain.indexOf('Состояние: ') !== 0 &&
          plain.indexOf('Плюсы материала: ') !== 0 &&
          plain.indexOf('Минусы материала: ') !== 0 &&
          plain.indexOf('Материал по физике близок к железу.') !== 0
        ) {
          lines.add(line)
        }
      }
    }
  } catch (e) {}

  lines.add(Text.aqua('◆ Материал рабочей части: ' + koshGearMaterialName(partStack)))

  var physics = koshGearPhysicsText(stack)
  if (physics.length > 0) {
    lines.add(Text.gray('Итоговая физика: ' + physics.join(' • ')))
  }

  var durability = koshGearDurabilitySummary(stack)
  if (durability) {
    var stateColor = durability.percent >= 70 ? Text.green
      : (durability.percent >= 35 ? Text.yellow : Text.red)
    lines.add(stateColor('Состояние: ' + durability.left + ' / ' + durability.max + ' • ' + durability.percent + '%'))
  }

  if (ironReference) {
    var positives = []
    var negatives = []

    var attack = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.ATTACK_DAMAGE)
    var ironAttack = koshGearNumber(ironReference, KOSH_GEAR_PROPERTIES.ATTACK_DAMAGE)
    var attackDelta = attack - ironAttack
    if (attackDelta > 0.01) positives.push('урон +' + koshGearFmt(attackDelta))
    if (attackDelta < -0.01) negatives.push('урон ' + koshGearFmt(attackDelta))

    var attackSpeed = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.ATTACK_SPEED)
    var ironAttackSpeed = koshGearNumber(ironReference, KOSH_GEAR_PROPERTIES.ATTACK_SPEED)
    var attackSpeedDelta = attackSpeed - ironAttackSpeed
    if (attackSpeedDelta > 0.01) positives.push('скорость атаки +' + koshGearFmt(attackSpeedDelta))
    if (attackSpeedDelta < -0.01) negatives.push('скорость атаки ' + koshGearFmt(attackSpeedDelta))

    var harvest = koshGearNumber(stack, KOSH_GEAR_PROPERTIES.HARVEST_SPEED)
    var ironHarvest = koshGearNumber(ironReference, KOSH_GEAR_PROPERTIES.HARVEST_SPEED)
    var harvestDelta = harvest - ironHarvest
    if (harvestDelta > 0.05) positives.push('скорость добычи +' + koshGearFmt(harvestDelta))
    if (harvestDelta < -0.05) negatives.push('скорость добычи ' + koshGearFmt(harvestDelta))

    var maxDamage = 0
    var ironMaxDamage = 0
    try { maxDamage = Number(stack.getMaxDamage()) } catch (e) {}
    try { ironMaxDamage = Number(ironReference.getMaxDamage()) } catch (e) {}

    if (ironMaxDamage > 0) {
      var durabilityPct = Math.round((maxDamage / ironMaxDamage - 1) * 100)
      if (durabilityPct > 0) positives.push('прочность +' + durabilityPct + '%')
      if (durabilityPct < 0) negatives.push('прочность ' + durabilityPct + '%')
    }

    if (positives.length > 0) lines.add(Text.green('Плюсы материала: ' + positives.join(', ')))
    if (negatives.length > 0) lines.add(Text.red('Минусы материала: ' + negatives.join(', ')))
    if (positives.length === 0 && negatives.length === 0) {
      lines.add(Text.darkGray('Материал по физике близок к железу.'))
    }
  }

  stack.set(KOSH_GEAR_DATA_COMPONENTS.LORE, new KOSH_GEAR_ITEM_LORE(lines))
}

function koshGearRefreshMaterialState(stack, partStack) {
  if (!stack || !partStack) return

  var ironReference = koshGearIronReference(stack, partStack)
  koshGearStampFrame(stack, partStack)
  koshGearMaterialLore(stack, partStack, ironReference)
}

function koshGearCurrentMainPartStack(stack) {
  try {
    var construction = KOSH_GEAR_DATA.getConstruction(stack)
    var primary = construction.getPrimaryPart()
    if (!primary) return null
    var partStack = primary.getItem()
    if (!partStack || partStack.empty) return null
    return partStack
  } catch (e) {}
  return null
}

ServerEvents.recipes(function(event) {
  KOSH_GEAR_SWAP_TYPES.forEach(function(row) {
    event.shapeless(row.gear, [row.gear, row.part])
      .modifyResult(KOSH_GEAR_MATERIAL_RESULT_EVENT)
      .id('kubejs:gear/material_swap/' + row.gear.split(':')[1])
  })
})

ServerEvents.modifyRecipeResult(KOSH_GEAR_MATERIAL_RESULT_EVENT, function(event) {
  var base = null
  var part = null
  var row = null

  try {
    // Read the actual crafting slots directly. In KubeJS 1.21.x, findAll()
    // can hand recipe-matching wrapper stacks that do not retain all live
    // components (damage/custom_data). grid.get(index) is the authoritative
    // ItemStack placed by the player.
    var gridSize = 9
    try {
      var w = Number(event.grid.width)
      var h = Number(event.grid.height)
      if (isFinite(w) && isFinite(h) && w > 0 && h > 0) gridSize = w * h
    } catch (e) {}

    for (var gridIndex = 0; gridIndex < gridSize; gridIndex++) {
      var stack = null
      try { stack = event.grid.get(gridIndex) } catch (e) {}
      if (!stack) continue

      var id = koshGearStackId(stack)
      if (!id || id === 'minecraft:air') continue

      if (KOSH_GEAR_BY_GEAR[id]) {
        base = stack
        row = KOSH_GEAR_BY_GEAR[id]
      } else if (KOSH_GEAR_BY_PART[id]) {
        part = stack
        if (!row) row = KOSH_GEAR_BY_PART[id]
      }
    }

    if (!base || !part || !row) return
    if (KOSH_GEAR_BY_PART[koshGearStackId(part)].gear !== koshGearStackId(base)) return

    var wear = koshGearWearFraction(base)
    var forgeSnapshot = koshGearForgeSnapshot(base)
    var customDataSnapshot = null
    try {
      var baseCustomData = base.getCustomData()
      if (baseCustomData) customDataSnapshot = baseCustomData.copy()
    } catch (e) {}

    var result = base.copy()
    result.count = 1

    var replacement = KOSH_GEAR_PART_INSTANCE.from(part)
    if (!replacement) return

    KOSH_GEAR_DATA.addOrReplacePart(result, replacement)
    try { replacement.onAddToGear(result) } catch (e) {}
    KOSH_GEAR_DATA.recalculateGearData(result, null)

    // Silent Gear is allowed to rebuild its own components, but player-owned
    // KoshPack custom_data must survive exactly. Restore the full snapshot first,
    // then explicitly restore forge slots for backwards compatibility.
    if (customDataSnapshot) {
      try { result.setCustomData(customDataSnapshot.copy()) } catch (e) {
        try { result.setCustomData(customDataSnapshot) } catch (_e) {}
      }
    }
    koshGearRestoreForgeSnapshot(result, forgeSnapshot)

    var newMax = 0
    try { newMax = Number(result.getMaxDamage()) } catch (e) {}
    if (newMax > 0) {
      var newDamage = Math.min(
        Math.max(0, Math.round(newMax * wear)),
        Math.max(0, newMax - 1)
      )

      // ItemStack#setDamageValue is the authoritative path here. Writing the raw
      // DAMAGE component directly can be overwritten/ignored by Silent Gear's
      // rebuilt stack during recipe preview.
      try {
        result.setDamageValue(newDamage)
      } catch (e) {
        try { result.damageValue = newDamage } catch (_e) {}
      }
    }

    // Rebuild the visible forge lines after Silent Gear recalculates the item.
    // The slot data is already restored above; this makes the preserved state
    // visible again in the result tooltip.
    try {
      if (typeof koshForgeRefreshLore === 'function') {
        koshForgeRefreshLore(result, 3, true)
      }
    } catch (e) {}

    // Always read the material back from the finished gear. The recipe grid can
    // hand us a transient part stack whose data no longer reflects the rebuilt
    // Silent Gear construction after result recalculation.
    var installedPart = koshGearCurrentMainPartStack(result)
    if (installedPart) koshGearRefreshMaterialState(result, installedPart)
    event.success(result)
  } catch (e) {
    console.error('[KoshPack Gear Material] swap failed: ' + e)
  }
})

// Initial assembly gets the same readable material summary as a later replacement.
ItemEvents.crafted(function(event) {
  var stack = event.item
  var id = koshGearStackId(stack)
  if (!KOSH_GEAR_BY_GEAR[id]) return

  var partStack = koshGearCurrentMainPartStack(stack)
  if (!partStack) return
  koshGearRefreshMaterialState(stack, partStack)
})
