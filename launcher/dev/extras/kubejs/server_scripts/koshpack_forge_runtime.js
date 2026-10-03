// KoshPack Forge modification runtime v0.4.
// Shared runtime for the expanded forge catalog.
// Numbers are the first live balance pass and are intentionally conservative.

var KOSH_RT_ATTRIBUTES = null
var KOSH_RT_ATTRIBUTE_MODIFIER = null
var KOSH_RT_RESOURCE_LOCATION = null
var KOSH_RT_BLOCK_POS = null
var KOSH_RT_BUILTIN_REGISTRIES = null
var KOSH_RT_MOB_EFFECTS = null
var KOSH_RT_REACTIVE_LATCH = {}
var KOSH_RT_DISCHARGE_STATE = {}

var KOSH_RT_OP_ADD = null
var KOSH_RT_OP_BASE = null
var KOSH_RT_TRENCHING_ACTIVE = false

if (typeof Java !== 'undefined') {
  KOSH_RT_ATTRIBUTES = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
  KOSH_RT_ATTRIBUTE_MODIFIER = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier')
  KOSH_RT_RESOURCE_LOCATION = Java.loadClass('net.minecraft.resources.ResourceLocation')
  KOSH_RT_BLOCK_POS = Java.loadClass('net.minecraft.core.BlockPos')
  KOSH_RT_BUILTIN_REGISTRIES = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')
  KOSH_RT_MOB_EFFECTS = Java.loadClass('net.minecraft.world.effect.MobEffects')
  KOSH_RT_OP_ADD = KOSH_RT_ATTRIBUTE_MODIFIER.Operation.ADD_VALUE
  KOSH_RT_OP_BASE = KOSH_RT_ATTRIBUTE_MODIFIER.Operation.ADD_MULTIPLIED_BASE
}

function koshRuntimeForgeSlot(stack, slot) {
  try {
    var tag = stack.getCustomData()
    var id = String(tag.getString('kosh_forge_slot_' + slot + '_id').orElse(''))
    var level = Number(tag.getInt('kosh_forge_slot_' + slot + '_level').orElse(0))
    if (id && level > 0) return { id: id, level: level }
  } catch (e) {}
  return null
}

function koshRuntimeForgeLevel(stack, modId) {
  if (!stack) return 0
  for (var i = 0; i < 3; i++) {
    var slot = koshRuntimeForgeSlot(stack, i)
    if (slot && slot.id === modId) return slot.level
  }
  return 0
}

function koshRuntimeAnyLevel(stack, ids) {
  var best = 0
  for (var i = 0; i < ids.length; i++) best = Math.max(best, koshRuntimeForgeLevel(stack, ids[i]))
  return best
}

function koshRuntimeArmor(player) {
  return [player.headArmorItem, player.chestArmorItem, player.legsArmorItem, player.feetArmorItem]
}

function koshRuntimeArmorLevels(player, modId) {
  var armor = koshRuntimeArmor(player)
  var out = []
  for (var i = 0; i < armor.length; i++) out.push(koshRuntimeForgeLevel(armor[i], modId))
  return out
}

function koshRuntimeArmorMax(player, modId) {
  var levels = koshRuntimeArmorLevels(player, modId)
  var max = 0
  for (var i = 0; i < levels.length; i++) max = Math.max(max, levels[i])
  return max
}

function koshRuntimeArmorSum(player, modId, values) {
  var levels = koshRuntimeArmorLevels(player, modId)
  var sum = 0
  for (var i = 0; i < levels.length; i++) {
    var lv = Math.max(0, Math.min(values.length - 1, levels[i]))
    sum += Number(values[lv] || 0)
  }
  return sum
}

function koshRuntimeSetDamage(event, multiplier) {
  multiplier = Math.max(0, Number(multiplier))
  try {
    var d = Number(event.damage)
    if (!isNaN(d)) {
      event.damage = Math.max(0, d * multiplier)
      return
    }
  } catch (e) {}
  try {
    var d2 = Number(event.getDamage())
    if (!isNaN(d2)) event.setDamage(Math.max(0, d2 * multiplier))
  } catch (e) {}
}

function koshRuntimeSourceActual(source) {
  try { if (source.actual) return source.actual } catch (e) {}
  try { return source.getActual() } catch (e) {}
  try { return source.getEntity() } catch (e) {}
  return null
}

function koshRuntimeSourceDirect(source) {
  try { if (source.direct) return source.direct } catch (e) {}
  try { return source.getDirectEntity() } catch (e) {}
  return null
}

function koshRuntimeSourceName(source) {
  try { return String(source.type()).toLowerCase() } catch (e) {}
  try { return String(source.getType()).toLowerCase() } catch (e) {}
  return ''
}

function koshRuntimeIsProjectile(source) {
  var n = koshRuntimeSourceName(source)
  if (/arrow|trident|projectile|bullet|shot/.test(n)) return true
  var actual = koshRuntimeSourceActual(source)
  var direct = koshRuntimeSourceDirect(source)
  if (actual && direct) {
    try { return String(actual.uuid) !== String(direct.uuid) } catch (e) {}
  }
  return false
}

function koshRuntimeIsExplosion(source) {
  return /explosion|explosive|blast/.test(koshRuntimeSourceName(source))
}

function koshRuntimeIsFire(source) {
  return /fire|lava|hot_floor|burn/.test(koshRuntimeSourceName(source))
}

function koshRuntimeIsFall(source) {
  return /fall|stalagmite/.test(koshRuntimeSourceName(source))
}

function koshRuntimeIsCollision(source) {
  return /fly_into_wall|collision|crash|impact/.test(koshRuntimeSourceName(source))
}

function koshRuntimeGeneralArmorEligible(source) {
  var n = koshRuntimeSourceName(source)
  return !/fall|out_of_world|outside_border|starve|in_wall|cramming|drown|freeze/.test(n)
}

function koshRuntimeMobType(entity) {
  try { return String(entity.getMobType()).toLowerCase() } catch (e) {}
  return ''
}

function koshRuntimeArmorValue(entity) {
  try { return Number(entity.armorValue) } catch (e) {}
  try { return Number(entity.getArmorValue()) } catch (e) {}
  return 0
}

function koshRuntimeRoll(entity, chance) {
  try { return entity.random.nextFloat() < chance } catch (e) {}
  try { return Math.random() < chance } catch (e) {}
  return false
}

function koshRuntimeAttr(name) {
  try { return KOSH_RT_ATTRIBUTES[name] } catch (e) {}
  return null
}

function koshRuntimeId(path) {
  try { return KOSH_RT_RESOURCE_LOCATION.fromNamespaceAndPath('koshpack', path) } catch (e) {}
  try { return KOSH_RT_RESOURCE_LOCATION.parse('koshpack:' + path) } catch (e) {}
  return null
}

function koshRuntimeSetAttr(player, attrName, idPath, amount, op) {
  var attr = koshRuntimeAttr(attrName)
  var id = koshRuntimeId(idPath)
  if (!attr || !id) return false
  try {
    player.modifyAttribute(attr, id, Number(amount), op)
    return true
  } catch (e) {}
  return false
}

function koshRuntimeRemoveAttr(player, attrName, idPath) {
  var attr = koshRuntimeAttr(attrName)
  var id = koshRuntimeId(idPath)
  if (!attr || !id) return
  try { player.removeAttribute(attr, id) } catch (e) {}
}

function koshRuntimeRegisteredAttr(attrId) {
  try {
    var rl = KOSH_RT_RESOURCE_LOCATION.parse(String(attrId))
    var attr = KOSH_RT_BUILTIN_REGISTRIES.ATTRIBUTE.get(rl)
    if (!attr) return null
    return KOSH_RT_BUILTIN_REGISTRIES.ATTRIBUTE.wrapAsHolder(attr)
  } catch (e) {}
  return null
}

function koshRuntimeSetRegisteredAttr(player, attrId, idPath, amount, op) {
  var attr = koshRuntimeRegisteredAttr(attrId)
  var id = koshRuntimeId(idPath)
  if (!attr || !id) return false
  try {
    player.modifyAttribute(attr, id, Number(amount), op)
    return true
  } catch (e) {}
  return false
}

function koshRuntimeRemoveRegisteredAttr(player, attrId, idPath) {
  var attr = koshRuntimeRegisteredAttr(attrId)
  var id = koshRuntimeId(idPath)
  if (!attr || !id) return
  try { player.removeAttribute(attr, id) } catch (e) {}
}

function koshRuntimeStackId(stack) {
  if (!stack) return ''
  try { return String(KOSH_RT_BUILTIN_REGISTRIES.ITEM.getKey(stack.getItem())) } catch (e) {}
  try { return String(stack.id) } catch (e) {}
  return ''
}

function koshRuntimeEntityId(entity) {
  if (!entity) return ''
  try { return String(KOSH_RT_BUILTIN_REGISTRIES.ENTITY_TYPE.getKey(entity.getType())) } catch (e) {}
  try { return String(entity.type) } catch (e) {}
  return ''
}

function koshRuntimePlayerKey(player) {
  try { return String(player.uuid) } catch (e) {}
  try { return String(player.getUUID()) } catch (e) {}
  return ''
}

function koshRuntimeBehind(attacker, victim) {
  try {
    var look = victim.getLookAngle()
    var dx = Number(attacker.x) - Number(victim.x)
    var dz = Number(attacker.z) - Number(victim.z)
    var len = Math.sqrt(dx * dx + dz * dz)
    if (len < 0.001) return false
    var dot = (Number(look.x) * dx + Number(look.z) * dz) / len
    return dot < -0.45
  } catch (e) {}
  return false
}

function koshRuntimeBelowId(player) {
  try {
    var b = player.level.getBlock(Math.floor(player.x), Math.floor(player.y - 0.15), Math.floor(player.z))
    return String(b.id)
  } catch (e) {}
  return ''
}

function koshRuntimeRefundOne(stack) {
  if (!stack) return
  try {
    var d = Number(stack.getDamageValue())
    if (d > 0) stack.setDamageValue(d - 1)
  } catch (e) {
    try {
      var d2 = Number(stack.damageValue)
      if (d2 > 0) stack.damageValue = d2 - 1
    } catch (_e) {}
  }
}

function koshRuntimeHeldDurabilityChance(stack) {
  var reinforced = koshRuntimeForgeLevel(stack, 'reinforced_frame')
  var tempered = koshRuntimeForgeLevel(stack, 'tempered_structure')
  var tool = koshRuntimeAnyLevel(stack, [
    'reinforced_neck','reinforced_socket','reinforced_eye','reinforced_core',
    'reinforced_lip','hardened_spine','reinforced_pivot','reinforced_handle','braided_line'
  ])
  var a = [0,0.15,0.25,0.35,0.45][Math.min(4, Math.max(reinforced, tool))]
  var b = [0,0.08,0.12,0.16,0.20][Math.min(4, tempered)]
  return Math.min(0.65, a + b)
}

function koshRuntimeTableValue(level, values) {
  var lv = Math.min(values.length - 1, Math.max(0, Number(level) || 0))
  return Number(values[lv] || 0)
}

function koshRuntimeForcedMiningSpeed(level) {
  return koshRuntimeTableValue(level, [0,0.18,0.36,0.54,0.72])
}

function koshRuntimeWorkPartOptimizationSpeed(level) {
  return koshRuntimeTableValue(level, [0,0.10,0.20,0.30,0.40])
}

function koshRuntimeForcedMiningExtraWear(level) {
  return koshRuntimeTableValue(level, [0,1,1,2,2])
}

function koshRuntimeTrenchingExtraBlocks(level) {
  return koshRuntimeTableValue(level, [0,1,2,3,4])
}

function koshRuntimeIsLooseTrenchingBlock(blockId) {
  var id = String(blockId || '').toLowerCase()
  return /(^|:)(dirt|coarse_dirt|rooted_dirt|grass_block|podzol|mycelium|sand|red_sand|gravel|clay|mud|snow|snow_block|soul_sand|soul_soil)$/.test(id)
}

function koshRuntimeTrenchingLine(origin, direction, level, shiftDown) {
  var count = koshRuntimeTrenchingExtraBlocks(level)
  if (shiftDown || count <= 0 || !origin || !direction) return []
  var dx = Number(direction.x) || 0
  var dy = Number(direction.y) || 0
  var dz = Number(direction.z) || 0
  var out = []
  for (var i = 1; i <= count; i++) {
    out.push({
      x: Math.floor(Number(origin.x) || 0) + dx * i,
      y: Math.floor(Number(origin.y) || 0) + dy * i,
      z: Math.floor(Number(origin.z) || 0) + dz * i
    })
  }
  return out
}

function koshRuntimeDirectionVector(name) {
  var n = String(name || '').toLowerCase()
  if (n.indexOf('north') >= 0) return { x: 0, y: 0, z: -1 }
  if (n.indexOf('south') >= 0) return { x: 0, y: 0, z: 1 }
  if (n.indexOf('west') >= 0) return { x: -1, y: 0, z: 0 }
  if (n.indexOf('east') >= 0) return { x: 1, y: 0, z: 0 }
  return null
}

function koshRuntimePlayerShiftDown(player) {
  try { if (player.isShiftKeyDown()) return true } catch (e) {}
  try { if (player.isCrouching()) return true } catch (e) {}
  try { if (player.shiftKeyDown) return true } catch (e) {}
  return false
}

function koshRuntimePlayerDigDirection(player) {
  try {
    var direct = koshRuntimeDirectionVector(player.getDirection())
    if (direct) return direct
  } catch (e) {}
  try {
    var named = koshRuntimeDirectionVector(player.direction)
    if (named) return named
  } catch (e) {}
  try {
    var yRot = Number(player.getYRot())
    if (!isNaN(yRot)) {
      var quadrant = Math.floor((yRot * 4 / 360) + 0.5) & 3
      return [
        { x: 0, y: 0, z: 1 },
        { x: -1, y: 0, z: 0 },
        { x: 0, y: 0, z: -1 },
        { x: 1, y: 0, z: 0 }
      ][quadrant]
    }
  } catch (e) {}
  return { x: 0, y: 0, z: 1 }
}

function koshRuntimePositionOrNull(x, y, z) {
  var nx = Number(x)
  var ny = Number(y)
  var nz = Number(z)
  if (!isNaN(nx) && !isNaN(ny) && !isNaN(nz)) return { x: nx, y: ny, z: nz }
  return null
}

function koshRuntimeBlockPosition(block) {
  try {
    var direct = koshRuntimePositionOrNull(block.x, block.y, block.z)
    if (direct) return direct
  } catch (e) {}
  try {
    var pos = block.pos
    var wrapped = koshRuntimePositionOrNull(pos.x, pos.y, pos.z)
    if (wrapped) return wrapped
  } catch (e) {}
  try {
    var p = block.blockPosition()
    return koshRuntimePositionOrNull(p.getX(), p.getY(), p.getZ())
  } catch (e) {}
  return null
}

function koshRuntimeDamageStack(stack, amount) {
  var extra = Math.max(0, Number(amount) || 0)
  if (!stack || extra <= 0) return
  try {
    var max = Number(stack.getMaxDamage())
    var damage = Number(stack.getDamageValue())
    if (max > 0 && !isNaN(damage)) stack.setDamageValue(Math.min(max - 1, damage + extra))
    return
  } catch (e) {}
  try {
    var max2 = Number(stack.maxDamage)
    var damage2 = Number(stack.damageValue)
    if (max2 > 0 && !isNaN(damage2)) stack.damageValue = Math.min(max2 - 1, damage2 + extra)
  } catch (_e) {}
}

function koshRuntimeDestroyLooseBlock(level, pos, player) {
  if (!level || !pos || !KOSH_RT_BLOCK_POS) return false
  try {
    var bp = new KOSH_RT_BLOCK_POS(pos.x, pos.y, pos.z)
    return level.destroyBlock(bp, true, player) === true
  } catch (e) {}
  try {
    var block = level.getBlock(pos.x, pos.y, pos.z)
    if (!block || !koshRuntimeIsLooseTrenchingBlock(block.id)) return false
    block.set('minecraft:air')
    return true
  } catch (_e) {}
  return false
}

function koshRuntimeToolSpeed(stack) {
  var groups = [
    ['aggressive_geometry',[0,0.18,0.36,0.54,0.72]],
    ['wide_blade',[0,0.10,0.20,0.30,0.40]],
    ['wide_cultivator',[0,0.10,0.20,0.30,0.40]],
    ['light_shaft',[0,0.05,0.10,0.15,0.20]],
    ['dual_angle',[0,0.06,0.12,0.18,0.24]],
    ['chisel_side',[0,0.10,0.20,0.30,0.40]],
    ['universal_balance',[0,0.06,0.12,0.18,0.24]],
    ['specialist_insert',[0,0.10,0.20,0.30,0.40]],
    ['wide_cut',[0,0.10,0.20,0.30,0.40]],
    ['soil_channels',[0,0.12,0.24,0.36,0.48]],
    ['coarse_teeth',[0,0.12,0.24,0.36,0.48]],
    ['fine_edge',[0,0.10,0.20,0.30,0.40]],
    ['wide_reaping',[0,0.10,0.20,0.30,0.40]]
  ]
  var best = 0
  for (var i = 0; i < groups.length; i++) {
    var lv = koshRuntimeForgeLevel(stack, groups[i][0])
    best = Math.max(best, Number(groups[i][1][Math.min(4, lv)] || 0))
  }
  return Math.min(0.75, best)
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    forcedMiningSpeed: koshRuntimeForcedMiningSpeed,
    workPartOptimizationSpeed: koshRuntimeWorkPartOptimizationSpeed,
    forcedMiningExtraWear: koshRuntimeForcedMiningExtraWear,
    isLooseTrenchingBlock: koshRuntimeIsLooseTrenchingBlock,
    trenchingLine: koshRuntimeTrenchingLine
  }
}

if (typeof EntityEvents !== 'undefined') EntityEvents.beforeHurt(event => {
  var victim = event.entity

  // ARMOR DEFENCE
  try {
    if (victim && victim.isPlayer && victim.isPlayer()) {
      var general = 0
      if (koshRuntimeGeneralArmorEligible(event.source)) {
        general = Math.min(0.20, koshRuntimeArmorSum(victim, 'reinforcement', [0,0.02,0.03,0.04,0.05]))
      }

      var specialized = 0
      if (koshRuntimeIsFire(event.source)) {
        specialized = Math.max(specialized, Math.min(0.40, koshRuntimeArmorSum(victim, 'thermal', [0,0.04,0.06,0.08,0.10])))
      }
      if (koshRuntimeIsExplosion(event.source)) {
        specialized = Math.max(specialized, Math.min(0.40, koshRuntimeArmorSum(victim, 'blast', [0,0.04,0.06,0.08,0.10])))
      }
      if (koshRuntimeIsProjectile(event.source)) {
        specialized = Math.max(specialized, Math.min(0.40, koshRuntimeArmorSum(victim, 'ballistic', [0,0.04,0.06,0.08,0.10])))
      }

      if (koshRuntimeIsFall(event.source)) {
        var cushion = koshRuntimeArmorMax(victim, 'cushion')
        specialized = Math.max(specialized, [0,0.15,0.30,0.45,0.60][Math.min(4,cushion)])
      }

      if (koshRuntimeIsCollision(event.source)) {
        var harness = koshRuntimeArmorMax(victim, 'harness')
        specialized = Math.max(specialized, [0,0.15,0.30,0.45,0.60][Math.min(4,harness)])
      }

      var reduction = 1.0 - (1.0 - general) * (1.0 - specialized)
      reduction = Math.min(0.75, Math.max(0, reduction))
      if (reduction > 0) koshRuntimeSetDamage(event, 1.0 - reduction)
    }
  } catch (e) {}

  // WEAPON / RANGED DAMAGE
  try {
    var attacker = koshRuntimeSourceActual(event.source)
    if (!attacker || !attacker.isPlayer || !attacker.isPlayer()) return
    var held = attacker.mainHandItem
    var projectile = koshRuntimeIsProjectile(event.source)
    var bonus = 0

    if (!projectile) {
      var fine = koshRuntimeForgeLevel(held, 'fine_honing')
      bonus += [0,0.04,0.08,0.12,0.16][Math.min(4,fine)]

      var silver = koshRuntimeForgeLevel(held, 'silvered_edge')
      if (silver > 0 && /undead/.test(koshRuntimeMobType(victim))) bonus += [0,0.08,0.16,0.24,0.32][Math.min(4,silver)]

      var serrated = koshRuntimeForgeLevel(held, 'serrated_edge')
      if (serrated > 0 && /arthropod/.test(koshRuntimeMobType(victim))) bonus += [0,0.06,0.12,0.18,0.24][Math.min(4,serrated)]

      var backstab = koshRuntimeForgeLevel(held, 'backstab_point')
      if (backstab > 0 && koshRuntimeBehind(attacker, victim)) {
        bonus += [0,0.40,0.80,1.20][Math.min(3,backstab)]
      }

    } else {
      var limbs = koshRuntimeForgeLevel(held, 'reinforced_limbs')
      var prod = koshRuntimeForgeLevel(held, 'reinforced_prod')
      bonus += Math.max(
        [0,0.05,0.10,0.15,0.20][Math.min(4,limbs)],
        [0,0.06,0.12,0.18,0.24][Math.min(4,prod)]
      )

      var voltaic = koshRuntimeForgeLevel(held, 'voltaic_guide')
      if (voltaic > 0) bonus += [0,0.05,0.10,0.15,0.20][Math.min(4,voltaic)]
    }

    if (bonus !== 0) koshRuntimeSetDamage(event, 1.0 + bonus)
  } catch (e) {}
})

if (typeof EntityEvents !== 'undefined') EntityEvents.afterHurt(event => {
  var victim = event.entity
  var attacker = koshRuntimeSourceActual(event.source)

  // THORNS: independent check per piece, max 4 damage per incoming melee hit.
  try {
    if (victim && victim.isPlayer && victim.isPlayer() && attacker && attacker !== victim && !koshRuntimeIsProjectile(event.source)) {
      var armor = koshRuntimeArmor(victim)
      var reflected = 0
      for (var i = 0; i < armor.length; i++) {
        var lv = koshRuntimeForgeLevel(armor[i], 'thorns')
        if (lv <= 0) continue
        var chance = [0,0.10,0.15,0.20,0.25][Math.min(4,lv)]
        var dmg = [0,1,1,2,2][Math.min(4,lv)]
        if (koshRuntimeRoll(victim, chance) && reflected < 4) {
          var dealt = Math.min(dmg, 4 - reflected)
          try { attacker.attack(dealt) } catch (e) {
            try { attacker.damage(dealt) } catch (_e) {}
          }
          reflected += dealt
        }
      }
    }
  } catch (e) {}

  // Armor hardening: probabilistically refunds ordinary wear after the hit.
  try {
    if (victim && victim.isPlayer && victim.isPlayer()) {
      var armor2 = koshRuntimeArmor(victim)
      victim.server.scheduleInTicks(1, function() {
        for (var i = 0; i < armor2.length; i++) {
          var lv = koshRuntimeForgeLevel(armor2[i], 'hardening')
          var chance = [0,0.10,0.20,0.30,0.40][Math.min(4,lv)]
          if (chance > 0 && koshRuntimeRoll(victim, chance)) koshRuntimeRefundOne(armor2[i])
        }
      })
    }
  } catch (e) {}

  // Offensive control / fire / knockback.
  try {
    if (!attacker || !attacker.isPlayer || !attacker.isPlayer()) return
    var held = attacker.mainHandItem
    var projectile = koshRuntimeIsProjectile(event.source)

    var fireLv = projectile ? koshRuntimeForgeLevel(held,'incendiary_setup') : koshRuntimeForgeLevel(held,'ignition_insert')
    if (fireLv > 0) {
      try { victim.igniteForSeconds([0,2,3,4,5][Math.min(4,fireLv)]) } catch (e) {}
    }

    var serrated = koshRuntimeForgeLevel(held,'serrated_edge')
    if (!projectile && serrated > 0 && /arthropod/.test(koshRuntimeMobType(victim))) {
      try { victim.potionEffects.add('minecraft:slowness', 20 + serrated * 10, 0, false, true) } catch (e) {}
    }

    var barb = koshRuntimeForgeLevel(held,'harpoon_barb')
    if (projectile && barb > 0) {
      try { victim.potionEffects.add('minecraft:slowness', 20 + barb * 10, 0, false, true) } catch (e) {}
    }

    var knock = koshRuntimeForgeLevel(held,'weighted_pommel')
    if (!projectile && knock > 0) {
      try {
        var dx = victim.x - attacker.x
        var dz = victim.z - attacker.z
        var len = Math.sqrt(dx*dx + dz*dz)
        if (len > 0.001) {
          var power = [0,0.10,0.20,0.30,0.40][Math.min(4,knock)]
          victim.addMotion(dx / len * power, 0.05, dz / len * power)
        }
      } catch (e) {}
    }

    var snare = koshRuntimeForgeLevel(held,'snare_module')
    if (!projectile && snare > 0 && koshRuntimeRoll(attacker,[0,0.15,0.25,0.35,0.45][Math.min(4,snare)])) {
      try { victim.potionEffects.add('minecraft:slowness', 30 + snare * 20, snare >= 3 ? 1 : 0, false, true) } catch (e) {}
    }

    var discharge = koshRuntimeForgeLevel(held,'kinetic_accumulator')
    if (!projectile && discharge > 0) {
      var dkey = koshRuntimePlayerKey(attacker)
      if (dkey) {
        var ds = KOSH_RT_DISCHARGE_STATE[dkey] || { count: 0, expires: 0 }
        ds.count += 1
        try { ds.expires = Number(attacker.tickCount) + 80 } catch (e) { ds.expires = 80 }
        var threshold = Math.max(2, 6 - discharge)
        if (ds.count >= threshold) {
          try { victim.attack(2 + discharge) } catch (e) {}
          try { attacker.attack(1 + discharge * 0.5) } catch (e) {}
          ds.count = 0
        }
        KOSH_RT_DISCHARGE_STATE[dkey] = ds
      }
    }

    var wearChance = koshRuntimeHeldDurabilityChance(held)
    if (wearChance > 0) {
      var heldRef = held
      attacker.server.scheduleInTicks(1, function() {
        if (koshRuntimeRoll(attacker, wearChance)) koshRuntimeRefundOne(heldRef)
      })
    }
  } catch (e) {}
})

if (typeof EntityEvents !== 'undefined') EntityEvents.spawned(event => {
  try {
    var entity = event.entity
    var owner = null
    try { owner = entity.getOwner() } catch (e) {}
    if (!owner || !owner.isPlayer || !owner.isPlayer()) return

    var held = owner.mainHandItem
    var eid = koshRuntimeEntityId(entity)
    var heldId = koshRuntimeStackId(held)

    var voltaic = koshRuntimeForgeLevel(held,'voltaic_guide')
    if (voltaic > 0 && /arrow|bolt|projectile/.test(eid)) {
      try { entity.setNoGravity(true) } catch (e) {}
    }

  } catch (e) {}
})

if (typeof EntityEvents !== 'undefined') EntityEvents.drops(event => {
  try {
    var attacker = koshRuntimeSourceActual(event.source)
    if (!attacker || !attacker.isPlayer || !attacker.isPlayer()) return
    var held = attacker.mainHandItem
    var lv = koshRuntimeForgeLevel(held, 'harvest_edge')
    if (lv <= 0) return

    var chance = [0,0.05,0.10,0.15,0.20][Math.min(4,lv)]
    if (!koshRuntimeRoll(attacker, chance)) return

    var drops = event.drops
    if (!drops || drops.size() <= 0) return
    var first = drops.get(0)
    if (!first) return
    var stack = first.item.copy()
    stack.count = 1
    event.addDrop(stack)
  } catch (e) {}
})

if (typeof BlockEvents !== 'undefined') BlockEvents.drops(event => {
  try {
    var player = event.entity
    var tool = event.tool
    if (!player || !tool) return

    // Precision Extraction: physical Silk Touch replacement.
    var silk = koshRuntimeForgeLevel(tool, 'precision_extraction')
    if (silk > 0) {
      try {
        var blockId = String(event.block.id)
        var blockStack = Item.of(blockId)
        if (blockStack && !blockStack.empty) {
          event.itemEntities.clear()
          var out = blockStack.copy()
          out.count = 1
          event.addItem(out)
        }
      } catch (e) {}
    } else {
      // Fortune / harvest-like physical treatments: modest extra single drop chance.
      var yieldLv = Math.max(
        koshRuntimeForgeLevel(tool,'fracture_control'),
        koshRuntimeForgeLevel(tool,'harvest_teeth'),
        koshRuntimeForgeLevel(tool,'fine_teeth'),
        koshRuntimeForgeLevel(tool,'harvest_stop'),
        koshRuntimeForgeLevel(tool,'fine_harvest')
      )
      if (yieldLv > 0) {
        var chance = [0,0.08,0.16,0.24,0.32][Math.min(4,yieldLv)]
        if (koshRuntimeRoll(player, chance)) {
          var items = event.items
          if (items && items.size() > 0) {
            var extra = items.get(0).copy()
            extra.count = 1
            event.addItem(extra)
          }
        }
      }
    }

    var forcedWear = koshRuntimeForcedMiningExtraWear(koshRuntimeForgeLevel(tool, 'aggressive_geometry'))
    if (forcedWear > 0) {
      var forcedToolRef = tool
      player.server.scheduleInTicks(1, function() {
        koshRuntimeDamageStack(forcedToolRef, forcedWear)
      })
    }

    var trenchLv = koshRuntimeForgeLevel(tool, 'trenching_edge')
    if (!KOSH_RT_TRENCHING_ACTIVE && trenchLv > 0 && !koshRuntimePlayerShiftDown(player)) {
      var origin = koshRuntimeBlockPosition(event.block)
      var sourceId = ''
      try { sourceId = String(event.block.id) } catch (e) {}
      if (origin && koshRuntimeIsLooseTrenchingBlock(sourceId)) {
        var level = null
        try { level = event.level } catch (e) {}
        try { if (!level) level = player.serverLevel() } catch (e) {}
        try { if (!level) level = player.level } catch (e) {}
        var line = koshRuntimeTrenchingLine(origin, koshRuntimePlayerDigDirection(player), trenchLv, false)
        KOSH_RT_TRENCHING_ACTIVE = true
        try {
          for (var li = 0; li < line.length; li++) {
            var target = line[li]
            var targetBlock = null
            try { targetBlock = level.getBlock(target.x, target.y, target.z) } catch (e) {}
            if (!targetBlock || !koshRuntimeIsLooseTrenchingBlock(targetBlock.id)) continue
            if (koshRuntimeDestroyLooseBlock(level, target, player)) koshRuntimeDamageStack(tool, 1)
          }
        } finally {
          KOSH_RT_TRENCHING_ACTIVE = false
        }
      }
    }

    var wearChance = koshRuntimeHeldDurabilityChance(tool)
    if (wearChance > 0) {
      var toolRef = tool
      player.server.scheduleInTicks(1, function() {
        if (koshRuntimeRoll(player, wearChance)) koshRuntimeRefundOne(toolRef)
      })
    }
  } catch (e) {}
})

function koshRuntimeApplyFrost(player, level) {
  if (level <= 0) return
  try {
    if (!player.onGround()) return
  } catch (e) {
    try { if (!player.onGround) return } catch (_e) {}
  }

  var radius = [0,2,3,4,5][Math.min(4,level)]
  var py = Math.floor(player.y - 0.15)
  var px = Math.floor(player.x)
  var pz = Math.floor(player.z)

  for (var dx = -radius; dx <= radius; dx++) {
    for (var dz = -radius; dz <= radius; dz++) {
      if (dx*dx + dz*dz > radius*radius) continue
      try {
        var below = player.level.getBlock(px + dx, py - 1, pz + dz)
        var above = player.level.getBlock(px + dx, py, pz + dz)
        if (String(below.id) === 'minecraft:water' && String(above.id) === 'minecraft:air') {
          below.set('minecraft:frosted_ice')
        }
      } catch (e) {}
    }
  }
}

if (typeof PlayerEvents !== 'undefined') PlayerEvents.tick(event => {
  var player = event.player

  // Fast attributes refresh every 5 ticks.
  try {
    if ((player.tickCount % 5) !== 0) return
  } catch (e) {
    return
  }

  var boots = player.feetArmorItem
  var legs = player.legsArmorItem
  var chest = player.chestArmorItem
  var helmet = player.headArmorItem
  var held = player.mainHandItem

  // Ground movement, capped at +30% from this forge system.
  var walking = koshRuntimeForgeLevel(boots,'walking')
  var ground = [0,0.03,0.06,0.09,0.12][Math.min(4,walking)]

  var soul = koshRuntimeForgeLevel(boots,'soul')
  var belowId = koshRuntimeBelowId(player)
  if (soul > 0 && (belowId === 'minecraft:soul_sand' || belowId === 'minecraft:soul_soil')) {
    ground += [0,0.08,0.10,0.20,0.30][Math.min(4,soul)]
  }
  ground = Math.min(0.30, ground)
  if (ground > 0) koshRuntimeSetAttr(player,'MOVEMENT_SPEED','forge_ground_speed',ground,KOSH_RT_OP_BASE)
  else koshRuntimeRemoveAttr(player,'MOVEMENT_SPEED','forge_ground_speed')

  // Sneak speed: vanilla baseline is around 30%; add only the forge delta.
  var sneak = koshRuntimeForgeLevel(legs,'sneaking')
  var sneakAdd = [0,0.15,0.30,0.45,0.60][Math.min(4,sneak)]
  if (sneakAdd > 0) koshRuntimeSetAttr(player,'SNEAKING_SPEED','forge_sneak_speed',sneakAdd,KOSH_RT_OP_ADD)
  else koshRuntimeRemoveAttr(player,'SNEAKING_SPEED','forge_sneak_speed')

  var aqua = koshRuntimeForgeLevel(helmet,'aqua_work')
  var aquaAdd = [0,0.20,0.40,0.60,0.80][Math.min(4,aqua)]
  if (aquaAdd > 0) koshRuntimeSetAttr(player,'SUBMERGED_MINING_SPEED','forge_submerged_mining',aquaAdd,KOSH_RT_OP_ADD)
  else koshRuntimeRemoveAttr(player,'SUBMERGED_MINING_SPEED','forge_submerged_mining')

  var hydro = koshRuntimeForgeLevel(boots,'hydrodynamic')
  var hydroAdd = [0,0.15,0.30,0.45,0.60][Math.min(4,hydro)]
  if (hydroAdd > 0) koshRuntimeSetAttr(player,'WATER_MOVEMENT_EFFICIENCY','forge_water_move',hydroAdd,KOSH_RT_OP_ADD)
  else koshRuntimeRemoveAttr(player,'WATER_MOVEMENT_EFFICIENCY','forge_water_move')

  var stability = koshRuntimeForgeLevel(chest,'stability')
  var kb = [0,0.10,0.20,0.30,0.40][Math.min(4,stability)]
  if (kb > 0) koshRuntimeSetAttr(player,'KNOCKBACK_RESISTANCE','forge_stability',kb,KOSH_RT_OP_ADD)
  else koshRuntimeRemoveAttr(player,'KNOCKBACK_RESISTANCE','forge_stability')

  var step = koshRuntimeForgeLevel(boots,'step')
  if (step > 0) koshRuntimeSetAttr(player,'STEP_HEIGHT','forge_step_height',0.40,KOSH_RT_OP_ADD)
  else koshRuntimeRemoveAttr(player,'STEP_HEIGHT','forge_step_height')

  var spring = koshRuntimeForgeLevel(boots,'spring')
  var jump = [0,0.08,0.16,0.24,0.32][Math.min(4,spring)]
  if (jump > 0) koshRuntimeSetAttr(player,'JUMP_STRENGTH','forge_jump_strength',jump,KOSH_RT_OP_BASE)
  else koshRuntimeRemoveAttr(player,'JUMP_STRENGTH','forge_jump_strength')

  var grip = koshRuntimeForgeLevel(boots,'grip')
  var ice = /ice/.test(belowId)
  var gripAdd = ice ? [0,0.25,0.50,0.75,1.00][Math.min(4,grip)] : 0
  if (gripAdd > 0) koshRuntimeSetAttr(player,'MOVEMENT_EFFICIENCY','forge_ice_grip',gripAdd,KOSH_RT_OP_ADD)
  else koshRuntimeRemoveAttr(player,'MOVEMENT_EFFICIENCY','forge_ice_grip')

  // Tool mining speed.
  var toolSpeed = koshRuntimeToolSpeed(held)
  if (toolSpeed > 0) {
    if (!koshRuntimeSetAttr(player,'BLOCK_BREAK_SPEED','forge_tool_speed',toolSpeed,KOSH_RT_OP_BASE)) {
      var amp = toolSpeed >= 0.30 ? 1 : 0
      try { player.potionEffects.add('minecraft:haste', 15, amp, true, false) } catch (e) {}
    }
  } else koshRuntimeRemoveAttr(player,'BLOCK_BREAK_SPEED','forge_tool_speed')

  // Weapon handling.
  var light = koshRuntimeForgeLevel(held,'light_grip')
  var heavy = koshRuntimeForgeLevel(held,'weighted_pommel')
  var attackSpeed = [0,0.03,0.06,0.09,0.12][Math.min(4,light)] - [0,0.03,0.06,0.09,0.12][Math.min(4,heavy)]
  if (attackSpeed !== 0) koshRuntimeSetAttr(player,'ATTACK_SPEED','forge_attack_speed',attackSpeed,KOSH_RT_OP_BASE)
  else koshRuntimeRemoveAttr(player,'ATTACK_SPEED','forge_attack_speed')

  var sweep = koshRuntimeForgeLevel(held,'wide_sweep')
  var sweepAmount = [0,0.08,0.12,0.16,0.20][Math.min(4,sweep)]
  if (sweepAmount > 0) koshRuntimeSetAttr(player,'SWEEPING_DAMAGE_RATIO','forge_sweeping_ratio',sweepAmount,KOSH_RT_OP_ADD)
  else koshRuntimeRemoveAttr(player,'SWEEPING_DAMAGE_RATIO','forge_sweeping_ratio')

  // Purification replacement: periodically neutralizes poison/wither while equipped.
  var purification = koshRuntimeArmorMax(player,'purification_filter')
  if (purification > 0 && (player.tickCount % 20) === 0) {
    var afflicted = false
    try { afflicted = player.hasEffect(KOSH_RT_MOB_EFFECTS.POISON) || player.hasEffect(KOSH_RT_MOB_EFFECTS.WITHER) } catch (e) {}
    if (afflicted && koshRuntimeRoll(player,[0,0.25,0.40,0.55,0.70][Math.min(4,purification)])) {
      try { player.removeEffect(KOSH_RT_MOB_EFFECTS.POISON) } catch (e) {}
      try { player.removeEffect(KOSH_RT_MOB_EFFECTS.WITHER) } catch (e) {}
    }
  }

  // Physical replacements for Combat Roll enchantments.
  var rollCount = koshRuntimeForgeLevel(helmet,'roll_capacity')
  if (rollCount > 0) koshRuntimeSetRegisteredAttr(player,'combat_roll:count','forge_roll_count',rollCount,KOSH_RT_OP_ADD)
  else koshRuntimeRemoveRegisteredAttr(player,'combat_roll:count','forge_roll_count')

  var rollRecharge = koshRuntimeForgeLevel(chest,'roll_recharge')
  if (rollRecharge > 0) koshRuntimeSetRegisteredAttr(player,'combat_roll:recharge','forge_roll_recharge',rollRecharge * 0.20,KOSH_RT_OP_BASE)
  else koshRuntimeRemoveRegisteredAttr(player,'combat_roll:recharge','forge_roll_recharge')

  var rollDistance = koshRuntimeForgeLevel(boots,'roll_distance')
  if (rollDistance > 0) koshRuntimeSetRegisteredAttr(player,'combat_roll:distance','forge_roll_distance',rollDistance,KOSH_RT_OP_ADD)
  else koshRuntimeRemoveRegisteredAttr(player,'combat_roll:distance','forge_roll_distance')

  // Hell Strider replacement: only active while actually in lava.
  var lavaTread = koshRuntimeForgeLevel(boots,'lava_tread')
  var inLava = false
  try { inLava = player.isInLava() } catch (e) {}
  if (lavaTread > 0 && inLava) koshRuntimeSetAttr(player,'MOVEMENT_SPEED','forge_lava_tread',[0,0.25,0.35][Math.min(2,lavaTread)],KOSH_RT_OP_BASE)
  else koshRuntimeRemoveAttr(player,'MOVEMENT_SPEED','forge_lava_tread')

  // Discharge replacement: accumulated hits temporarily build movement speed.
  var dischargeLevel = koshRuntimeForgeLevel(held,'kinetic_accumulator')
  var dischargeKey = koshRuntimePlayerKey(player)
  var dischargeState = dischargeKey ? KOSH_RT_DISCHARGE_STATE[dischargeKey] : null
  var nowTick = 0
  try { nowTick = Number(player.tickCount) } catch (e) {}
  if (dischargeState && dischargeState.expires > 0 && nowTick > dischargeState.expires) {
    delete KOSH_RT_DISCHARGE_STATE[dischargeKey]
    dischargeState = null
  }
  if (dischargeLevel > 0 && dischargeState && dischargeState.count > 0) {
    var dischargeSpeed = Math.min(0.24, dischargeState.count * 0.03 * dischargeLevel)
    koshRuntimeSetAttr(player,'MOVEMENT_SPEED','forge_discharge_speed',dischargeSpeed,KOSH_RT_OP_BASE)
  } else {
    koshRuntimeRemoveAttr(player,'MOVEMENT_SPEED','forge_discharge_speed')
  }

  // Fishing luck portion of Fine Hook.
  var hook = koshRuntimeForgeLevel(held,'fine_hook')
  if (hook > 0) koshRuntimeSetAttr(player,'LUCK','forge_fishing_luck',hook,KOSH_RT_OP_ADD)
  else koshRuntimeRemoveAttr(player,'LUCK','forge_fishing_luck')

  // Breathing reserve approximation: restore air slowly while submerged.
  var breathing = koshRuntimeForgeLevel(helmet,'breathing')
  if (breathing > 0) {
    try {
      if (player.isUnderWater()) {
        var air = Number(player.getAirSupply())
        player.setAirSupply(Math.min(300 + breathing * 300, air + breathing))
      }
    } catch (e) {}
  }

  // Freeze accumulation reduction, sum capped at 80%.
  var lining = Math.min(0.80, koshRuntimeArmorSum(player,'lining',[0,0.10,0.15,0.20,0.25]))
  if (lining > 0) {
    try {
      var frozen = Number(player.getTicksFrozen())
      if (frozen > 0 && (player.tickCount % 10) === 0) {
        player.setTicksFrozen(Math.max(0, frozen - Math.max(1, Math.floor(10 * lining))))
      }
    } catch (e) {}
  }

  // Streamlined chest offsets part of bow/shield use slowdown.
  var stream = koshRuntimeForgeLevel(chest,'streamline')
  var using = false
  try { using = player.isUsingItem() } catch (e) {}
  if (stream > 0 && using) {
    var offset = [0,0.03,0.06,0.09,0.12][Math.min(4,stream)]
    koshRuntimeSetAttr(player,'MOVEMENT_SPEED','forge_streamline',offset,KOSH_RT_OP_BASE)
  } else koshRuntimeRemoveAttr(player,'MOVEMENT_SPEED','forge_streamline')

  // Reactive Shaft: physical Riptide replacement. Triggers once after a short trident charge.
  var reactive = koshRuntimeForgeLevel(held,'reactive_shaft')
  var wet = false
  try { wet = player.isInWater() || player.isInRain() } catch (e) {
    try { wet = player.isInWater() } catch (_e) {}
  }
  var reactiveKey = ''
  try { reactiveKey = String(player.uuid) } catch (e) {
    try { reactiveKey = String(player.getUUID()) } catch (_e) {}
  }
  var useTicks = 0
  try { useTicks = Number(player.getTicksUsingItem()) } catch (e) {}
  var reactiveTridentId = koshRuntimeStackId(held)
  if (reactive > 0 && using && wet && (reactiveTridentId === 'minecraft:trident' || reactiveTridentId === 'silentgear:trident')) {
    if (useTicks >= 10 && !KOSH_RT_REACTIVE_LATCH[reactiveKey]) {
      try {
        var look = player.getLookAngle()
        var thrust = [0,1.05,1.25,1.45,1.65][Math.min(4,reactive)]
        player.addMotion(Number(look.x) * thrust, Number(look.y) * thrust + 0.15, Number(look.z) * thrust)
        KOSH_RT_REACTIVE_LATCH[reactiveKey] = true
        try { player.stopUsingItem() } catch (_e) {}
      } catch (e) {}
    }
  } else if (reactiveKey) {
    delete KOSH_RT_REACTIVE_LATCH[reactiveKey]
  }

  // Frosted ice generation.
  var frost = koshRuntimeForgeLevel(boots,'frost')
  if (frost > 0 && (player.tickCount % 10) === 0) koshRuntimeApplyFrost(player,frost)
})
