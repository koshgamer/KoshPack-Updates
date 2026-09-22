// KoshPack Forge modification runtime v0.1.
// Vertical-slice effects for the shared armor / weapon / tool forge data model.

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

function koshRuntimeSetDamage(event, multiplier) {
  try {
    var damage = Number(event.damage)
    if (!isNaN(damage)) {
      event.damage = Math.max(0, damage * multiplier)
      return
    }
  } catch (e) {}
  try {
    var damage2 = Number(event.getDamage())
    if (!isNaN(damage2)) event.setDamage(Math.max(0, damage2 * multiplier))
  } catch (e) {}
}

function koshRuntimeSourceActual(source) {
  try { if (source.actual) return source.actual } catch (e) {}
  try { return source.getActual() } catch (e) {}
  try { return source.getEntity() } catch (e) {}
  return null
}

function koshRuntimeIsProjectile(source) {
  var type = ''
  try { type = String(source.type()).toLowerCase() } catch (e) {}
  if (/arrow|trident|projectile|bullet|shot/.test(type)) return true

  var actual = koshRuntimeSourceActual(source)
  var direct = null
  try { direct = source.direct } catch (e) {}
  try { if (!direct) direct = source.getDirectEntity() } catch (e) {}

  if (actual && direct) {
    try { return String(actual.uuid) !== String(direct.uuid) } catch (e) {}
  }
  return false
}

EntityEvents.beforeHurt(event => {
  // Armor reinforcement: one item's I/II/III/IV = 2/3/4/5%; four pieces cap at 20%.
  try {
    var victim = event.entity
    if (victim && victim.isPlayer()) {
      var armor = [victim.headArmorItem, victim.chestArmorItem, victim.legsArmorItem, victim.feetArmorItem]
      var pct = 0
      var vals = [0, 0.02, 0.03, 0.04, 0.05]
      for (var i = 0; i < armor.length; i++) {
        var lv = koshRuntimeForgeLevel(armor[i], 'reinforcement')
        pct += vals[Math.max(0, Math.min(4, lv))]
      }
      pct = Math.min(0.20, pct)
      if (pct > 0) koshRuntimeSetDamage(event, 1.0 - pct)
    }
  } catch (e) {}

  // Fine Honing: melee-only +4/8/12/16% in the first live balance slice.
  try {
    var attacker = koshRuntimeSourceActual(event.source)
    if (!attacker || !attacker.isPlayer || !attacker.isPlayer()) return
    if (koshRuntimeIsProjectile(event.source)) return

    var level = koshRuntimeForgeLevel(attacker.mainHandItem, 'fine_honing')
    if (level > 0) {
      var bonus = [0, 0.04, 0.08, 0.12, 0.16][Math.min(4, level)]
      koshRuntimeSetDamage(event, 1.0 + bonus)
    }
  } catch (e) {}
})

PlayerEvents.tick(event => {
  var player = event.player
  try {
    if ((player.tickCount % 20) !== 0) return
  } catch (e) {
    return
  }

  var level = koshRuntimeForgeLevel(player.mainHandItem, 'aggressive_geometry')
  if (level <= 0) return

  // v0.1 live slice. Haste I for I-II, Haste II for III-IV.
  var amp = level >= 3 ? 1 : 0
  try {
    player.potionEffects.add('minecraft:haste', 50, amp, true, false)
  } catch (e) {
    try { player.potionEffects.add('minecraft:haste', 50, amp) } catch (_e) {}
  }
})
