// KoshPack professional armor traits v1.
// Real gameplay bonuses + drawbacks for all 17 profession sets.
// A profession trait activates when all four equipped pieces belong to the same profession.
// Mixed tiers are allowed; the effective trait tier is the LOWEST of the four equipped pieces.

var KOSHPACK_ARMOR_ROLE_BY_NAMESPACE = {
  'koshpackminerhelmet': 'miner',
  'koshpackengineerhelmet': 'engineer',
  'koshpackscouthelmet': 'scout',
  'koshpackbuilderhelmet': 'builder',
  'koshpackmedichelmet': 'medic',
  'koshpackfarmerhelmet': 'farmer',
  'koshpackblacksmithhelmet': 'blacksmith',
  'koshpackfisherhelmet': 'fisher',
  'koshpacklumberjackhelmet': 'lumberjack',
  'koshpackdiverhelmet': 'diver',
  'koshpackfighterarmor': 'fighter',
  'koshpackarcherarmor': 'archer',
  'koshpackshooterarmor': 'shooter',
  'koshpackartilleryarmor': 'artillery',
  'koshpackhunterarmor': 'hunter',
  'koshpackresearcherarmor': 'researcher',
  'koshpackpilothelmet': 'pilot'
}

var KOSHPACK_ARMOR_PREFIX = {
  miner: 'miner',
  engineer: 'engineer',
  scout: 'scout',
  builder: 'builder',
  medic: 'medic',
  farmer: 'farmer',
  blacksmith: 'blacksmith',
  fisher: 'fisher',
  lumberjack: 'lumberjack',
  diver: 'diver',
  fighter: 'fighter',
  archer: 'archer',
  shooter: 'shooter',
  artillery: 'artillery',
  hunter: 'hunter',
  researcher: 'researcher',
  pilot: 'pilot'
}

function koshArmorStackId(stack) {
  if (!stack) return ''
  try {
    if (stack.empty) return ''
  } catch (e) {}
  try { return String(stack.id) } catch (e) {}
  try { return String(stack.getId()) } catch (e) {}
  return ''
}

function koshArmorPieceInfo(stack) {
  var id = koshArmorStackId(stack)
  if (!id || id.indexOf(':') < 0) return null

  var split = id.split(':')
  var namespace = split[0]
  var path = split[1]
  var role = KOSHPACK_ARMOR_ROLE_BY_NAMESPACE[namespace]
  if (!role) return null

  var prefix = KOSHPACK_ARMOR_PREFIX[role]
  var match = path.match(new RegExp('^' + prefix + '_(helmet|chestplate|leggings|boots)_(i|ii|iii|iv)_test$'))
  if (!match) return null

  var tierMap = { i: 1, ii: 2, iii: 3, iv: 4 }
  return { role: role, piece: match[1], tier: tierMap[match[2]] }
}

function koshArmorSet(player) {
  var infos = [
    koshArmorPieceInfo(player.headArmorItem),
    koshArmorPieceInfo(player.chestArmorItem),
    koshArmorPieceInfo(player.legsArmorItem),
    koshArmorPieceInfo(player.feetArmorItem)
  ]

  for (var i = 0; i < infos.length; i++) {
    if (!infos[i]) return null
  }

  var role = infos[0].role
  var seen = {}
  var minTier = 4
  for (var j = 0; j < infos.length; j++) {
    var info = infos[j]
    if (info.role !== role) return null
    seen[info.piece] = true
    minTier = Math.min(minTier, info.tier)
  }

  if (!seen.helmet || !seen.chestplate || !seen.leggings || !seen.boots) return null
  return { role: role, tier: minTier }
}

function koshAddEffect(player, effect, duration, amplifier) {
  try {
    player.potionEffects.add(effect, duration, amplifier, true, false)
  } catch (e) {
    try { player.potionEffects.add(effect, duration, amplifier) } catch (_e) {}
  }
}

function koshInWater(player) {
  try { return player.isInWater() } catch (e) {}
  try { return !!player.inWater } catch (e) {}
  return false
}

function koshSprinting(player) {
  try { return player.isSprinting() } catch (e) {}
  try { return !!player.sprinting } catch (e) {}
  return false
}

function koshAddExhaustion(player, amount) {
  try { player.addExhaustion(amount) } catch (e) {}
}

function koshSourceActual(source) {
  try { if (source.actual) return source.actual } catch (e) {}
  try { return source.getActual() } catch (e) {}
  try { return source.getEntity() } catch (e) {}
  return null
}

function koshSourceDirect(source) {
  try { if (source.direct) return source.direct } catch (e) {}
  try { return source.getDirectEntity() } catch (e) {}
  return null
}

function koshDamageType(source) {
  try { return String(source.type()) } catch (e) {}
  try { return String(source.getType()) } catch (e) {}
  try { return String(source.type) } catch (e) {}
  return ''
}

function koshIsProjectile(source) {
  var type = koshDamageType(source).toLowerCase()
  if (
    type.indexOf('arrow') >= 0 ||
    type.indexOf('trident') >= 0 ||
    type.indexOf('projectile') >= 0 ||
    type.indexOf('bullet') >= 0 ||
    type.indexOf('shot') >= 0
  ) return true

  var actual = koshSourceActual(source)
  var direct = koshSourceDirect(source)
  if (actual && direct) {
    try { return String(actual.uuid) !== String(direct.uuid) } catch (e) {}
  }
  return false
}

function koshIsExplosion(source) {
  var type = koshDamageType(source).toLowerCase()
  return type.indexOf('explosion') >= 0
}

function koshIsFire(source) {
  var type = koshDamageType(source).toLowerCase()
  return type.indexOf('fire') >= 0 || type.indexOf('lava') >= 0 || type.indexOf('hot_floor') >= 0
}

function koshIsFall(source) {
  return koshDamageType(source).toLowerCase().indexOf('fall') >= 0
}

function koshIsEnvironmental(source) {
  var type = koshDamageType(source).toLowerCase()
  return (
    type.indexOf('fall') >= 0 ||
    type.indexOf('fire') >= 0 ||
    type.indexOf('lava') >= 0 ||
    type.indexOf('drown') >= 0 ||
    type.indexOf('freeze') >= 0 ||
    type.indexOf('cactus') >= 0 ||
    type.indexOf('magic') >= 0 ||
    type.indexOf('wither') >= 0
  )
}

function koshIsAxeLike(player) {
  var stack = player.mainHandItem
  try {
    if (stack && stack.hasTag && stack.hasTag('minecraft:axes')) return true
  } catch (e) {}
  var id = koshArmorStackId(stack).toLowerCase()
  return id.indexOf('axe') >= 0
}

function koshSetDamage(event, multiplier) {
  if (!event || multiplier === 1) return
  try {
    var value = Number(event.damage)
    if (!isNaN(value)) {
      event.damage = Math.max(0, value * multiplier)
      return
    }
  } catch (e) {}
  try {
    var value2 = Number(event.getDamage())
    if (!isNaN(value2) && event.setDamage) event.setDamage(Math.max(0, value2 * multiplier))
  } catch (e) {}
}

PlayerEvents.tick(event => {
  var player = event.player
  try {
    if ((player.tickCount % 20) !== 0) return
  } catch (e) {
    return
  }

  var set = koshArmorSet(player)
  if (!set) return

  var tier = set.tier
  var role = set.role
  var inWater = koshInWater(player)

  if (role === 'miner') {
    koshAddEffect(player, 'minecraft:haste', 50, tier >= 4 ? 1 : 0)
    if (tier >= 3) koshAddEffect(player, 'minecraft:night_vision', 260, 0)
    if (koshSprinting(player)) koshAddExhaustion(player, 0.06 + 0.015 * tier)
  }

  else if (role === 'engineer') {
    koshAddEffect(player, 'minecraft:haste', 50, tier >= 4 ? 1 : 0)
    if (tier >= 3) koshAddEffect(player, 'minecraft:fire_resistance', 50, 0)
  }

  else if (role === 'scout') {
    koshAddEffect(player, 'minecraft:speed', 50, tier >= 4 ? 1 : 0)
    if (tier >= 3) koshAddEffect(player, 'minecraft:jump_boost', 50, 0)
  }

  else if (role === 'builder') {
    koshAddEffect(player, 'minecraft:haste', 50, tier >= 4 ? 1 : 0)
    if (tier >= 2) koshAddEffect(player, 'minecraft:jump_boost', 50, 0)
    if (koshSprinting(player)) koshAddExhaustion(player, 0.05 + 0.01 * tier)
  }

  else if (role === 'medic') {
    var interval = tier === 1 ? 200 : tier === 2 ? 160 : tier === 3 ? 120 : 80
    if ((player.tickCount % interval) === 0) {
      koshAddEffect(player, 'minecraft:regeneration', tier >= 4 ? 80 : 60, tier >= 4 ? 1 : 0)
    }
  }

  else if (role === 'farmer') {
    koshAddEffect(player, 'minecraft:luck', 50, tier >= 4 ? 1 : 0)
    var foodInterval = tier === 1 ? 700 : tier === 2 ? 600 : tier === 3 ? 500 : 400
    if ((player.tickCount % foodInterval) === 0) {
      try { player.foodLevel = Math.min(20, player.foodLevel + 1) } catch (e) {}
    }
  }

  else if (role === 'blacksmith') {
    koshAddEffect(player, 'minecraft:fire_resistance', 50, 0)
    if (koshSprinting(player)) koshAddExhaustion(player, 0.08 + 0.015 * tier)
  }

  else if (role === 'fisher') {
    koshAddEffect(player, 'minecraft:luck', 50, tier >= 4 ? 1 : 0)
    if (inWater) {
      koshAddEffect(player, 'minecraft:dolphins_grace', 50, 0)
      if (tier >= 3) koshAddEffect(player, 'minecraft:water_breathing', 50, 0)
    }
  }

  else if (role === 'lumberjack') {
    koshAddEffect(player, 'minecraft:haste', 50, tier >= 4 ? 1 : 0)
    if (koshSprinting(player)) koshAddExhaustion(player, 0.06 + 0.015 * tier)
  }

  else if (role === 'diver') {
    if (inWater) {
      koshAddEffect(player, 'minecraft:water_breathing', 50, 0)
      koshAddEffect(player, 'minecraft:dolphins_grace', 50, tier >= 4 ? 1 : 0)
      if (tier >= 2) koshAddEffect(player, 'minecraft:night_vision', 260, 0)
    } else {
      koshAddEffect(player, 'minecraft:slowness', 50, 0)
      if (koshSprinting(player)) koshAddExhaustion(player, 0.10 + 0.02 * tier)
    }
  }

  else if (role === 'fighter') {
    koshAddEffect(player, 'minecraft:mining_fatigue', 50, 0)
  }

  else if (role === 'archer') {
    koshAddEffect(player, 'minecraft:speed', 50, tier >= 4 ? 1 : 0)
    if (tier >= 3) koshAddEffect(player, 'minecraft:jump_boost', 50, 0)
  }

  else if (role === 'shooter') {
    if (tier >= 3) koshAddEffect(player, 'minecraft:speed', 50, 0)
    if (koshSprinting(player)) koshAddExhaustion(player, 0.04 + 0.01 * tier)
  }

  else if (role === 'artillery') {
    koshAddEffect(player, 'minecraft:slowness', 50, 0)
    if (tier >= 3) koshAddEffect(player, 'minecraft:fire_resistance', 50, 0)
  }

  else if (role === 'hunter') {
    koshAddEffect(player, 'minecraft:speed', 50, tier >= 4 ? 1 : 0)
    if (tier >= 2) koshAddEffect(player, 'minecraft:night_vision', 260, 0)
  }

  else if (role === 'researcher') {
    koshAddEffect(player, 'minecraft:luck', 50, tier >= 4 ? 1 : 0)
    if (tier >= 2) koshAddEffect(player, 'minecraft:night_vision', 260, 0)
  }

  else if (role === 'pilot') {
    koshAddEffect(player, 'minecraft:slow_falling', 50, 0)
    koshAddEffect(player, 'minecraft:speed', 50, tier >= 4 ? 1 : 0)
    koshAddEffect(player, 'minecraft:mining_fatigue', 50, 0)
  }
})

EntityEvents.hurt(event => {
  var source = event.source

  // Incoming modifiers.
  try {
    if (event.entity && event.entity.isPlayer && event.entity.isPlayer()) {
      var victim = event.entity
      var set = koshArmorSet(victim)
      if (set) {
        var t = set.tier
        var r = set.role
        var mult = 1.0

        if (r === 'engineer' && koshIsFire(source)) {
          mult *= [1.0, 0.90, 0.85, 0.80, 0.70][t]
        } else if (r === 'scout') {
          if (koshIsFall(source)) mult *= [1.0, 0.80, 0.70, 0.60, 0.50][t]
          else mult *= 1.06
        } else if (r === 'builder' && koshIsFall(source)) {
          mult *= [1.0, 0.85, 0.78, 0.72, 0.65][t]
        } else if (r === 'blacksmith' && koshIsFire(source)) {
          mult *= [1.0, 0.75, 0.60, 0.45, 0.30][t]
        } else if (r === 'fighter') {
          mult *= [1.0, 0.96, 0.93, 0.90, 0.86][t]
        } else if (r === 'artillery') {
          if (koshIsExplosion(source)) mult *= [1.0, 0.80, 0.70, 0.60, 0.50][t]
          else mult *= [1.0, 0.98, 0.97, 0.95, 0.92][t]
        } else if (r === 'hunter') {
          mult *= 1.04
        } else if (r === 'researcher' && koshIsEnvironmental(source)) {
          mult *= [1.0, 0.92, 0.88, 0.84, 0.80][t]
        } else if (r === 'pilot') {
          if (koshIsFall(source)) mult *= [1.0, 0.30, 0.15, 0.05, 0.0][t]
          else mult *= 1.05
        }

        koshSetDamage(event, mult)
      }
    }
  } catch (e) {}

  // Outgoing modifiers.
  var attacker = koshSourceActual(source)
  try {
    if (!attacker || !attacker.isPlayer || !attacker.isPlayer()) return
  } catch (e) {
    return
  }

  var aset = koshArmorSet(attacker)
  if (!aset) return

  var tier = aset.tier
  var role = aset.role
  var projectile = koshIsProjectile(source)
  var explosion = koshIsExplosion(source)
  var out = 1.0

  if (role === 'engineer' && !projectile && !explosion) {
    out *= [1.0, 0.96, 0.95, 0.94, 0.92][tier]
  } else if (role === 'medic') {
    out *= 0.90
  } else if (role === 'farmer') {
    out *= 0.94
  } else if (role === 'blacksmith' && !projectile && !explosion) {
    out *= [1.0, 1.04, 1.06, 1.08, 1.10][tier]
  } else if (role === 'fisher' && !projectile && !explosion) {
    out *= 0.95
  } else if (role === 'lumberjack' && !projectile && !explosion && koshIsAxeLike(attacker)) {
    out *= [1.0, 1.04, 1.06, 1.08, 1.10][tier]
  } else if (role === 'fighter' && !projectile && !explosion) {
    out *= [1.0, 1.03, 1.05, 1.07, 1.10][tier]
  } else if (role === 'archer') {
    out *= projectile
      ? [1.0, 1.05, 1.08, 1.11, 1.15][tier]
      : 0.90
  } else if (role === 'shooter') {
    out *= projectile
      ? [1.0, 1.07, 1.10, 1.14, 1.18][tier]
      : 0.88
  } else if (role === 'artillery' && explosion) {
    out *= [1.0, 1.04, 1.07, 1.10, 1.15][tier]
  } else if (role === 'hunter') {
    if (projectile) out *= [1.0, 1.04, 1.07, 1.10, 1.12][tier]
  } else if (role === 'researcher' && !projectile && !explosion) {
    out *= 0.85
  }

  koshSetDamage(event, out)
})
