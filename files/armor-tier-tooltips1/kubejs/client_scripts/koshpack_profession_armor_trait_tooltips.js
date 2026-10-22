// KoshPack professional armor trait tooltips v2.
// Shows the REAL bonus/drawback of the tier the player actually wears
// (mirrors server_scripts/koshpack_profession_armor_traits.js — keep numbers in sync).
// Full set of one profession -> "active (tier N)" + that tier's lines.
// Otherwise -> "not active: worn K of 4" + lines of the hovered piece's tier.

var KoshTraitMinecraft = Java.loadClass('net.minecraft.client.Minecraft')
var KoshTraitSlot = Java.loadClass('net.minecraft.world.entity.EquipmentSlot')
var KoshTraitRegistries = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')

var KOSHPACK_TRAIT_IDS = {
  miner: 'koshpackminerhelmet',
  engineer: 'koshpackengineerhelmet',
  scout: 'koshpackscouthelmet',
  builder: 'koshpackbuilderhelmet',
  medic: 'koshpackmedichelmet',
  farmer: 'koshpackfarmerhelmet',
  blacksmith: 'koshpackblacksmithhelmet',
  fisher: 'koshpackfisherhelmet',
  lumberjack: 'koshpacklumberjackhelmet',
  diver: 'koshpackdiverhelmet',
  fighter: 'koshpackfighterarmor',
  archer: 'koshpackarcherarmor',
  shooter: 'koshpackshooterarmor',
  artillery: 'koshpackartilleryarmor',
  hunter: 'koshpackhunterarmor',
  researcher: 'koshpackresearcherarmor',
  pilot: 'koshpackpilothelmet'
}

var KOSH_TRAIT_ROMAN = ['', 'I', 'II', 'III', 'IV']

function koshTraitPct(values, tier) {
  return values[tier] + '%'
}

function koshTraitLvl(tier) {
  return tier >= 4 ? 'II' : 'I'
}

// Returns { plus: [...], minus: [...] } for the given role and tier (1..4).
function koshTraitLines(role, t) {
  var plus = []
  var minus = []

  if (role === 'miner') {
    plus.push('+ Спешка ' + koshTraitLvl(t) + ' (быстрее добыча)')
    if (t >= 3) plus.push('+ Ночное зрение')
    minus.push('− Спринт быстрее расходует сытость')
  } else if (role === 'engineer') {
    plus.push('+ Спешка ' + koshTraitLvl(t) + ' (быстрее работа)')
    plus.push('+ Урон от огня −' + koshTraitPct([0, 10, 15, 20, 30], t))
    if (t >= 3) plus.push('+ Огнестойкость')
    minus.push('− Урон в ближнем бою −' + koshTraitPct([0, 4, 5, 6, 8], t))
  } else if (role === 'scout') {
    plus.push('+ Скорость ' + koshTraitLvl(t))
    if (t >= 3) plus.push('+ Прыгучесть I')
    plus.push('+ Урон от падения −' + koshTraitPct([0, 20, 30, 40, 50], t))
    minus.push('− Прочий входящий урон +6%')
  } else if (role === 'builder') {
    plus.push('+ Спешка ' + koshTraitLvl(t) + ' (быстрее работа)')
    if (t >= 2) plus.push('+ Прыгучесть I')
    plus.push('+ Урон от падения −' + koshTraitPct([0, 15, 22, 28, 35], t))
    minus.push('− Спринт быстрее расходует сытость')
  } else if (role === 'medic') {
    var every = [0, 10, 8, 6, 4][t]
    plus.push('+ Регенерация ' + koshTraitLvl(t) + ' каждые ' + every + ' сек.')
    minus.push('− Наносимый урон −10%')
  } else if (role === 'farmer') {
    plus.push('+ Удача ' + koshTraitLvl(t))
    plus.push('+ 1 ед. сытости каждые ' + [0, 35, 30, 25, 20][t] + ' сек.')
    minus.push('− Наносимый урон −6%')
  } else if (role === 'blacksmith') {
    plus.push('+ Огнестойкость')
    plus.push('+ Урон от огня −' + koshTraitPct([0, 25, 40, 55, 70], t))
    plus.push('+ Урон в ближнем бою +' + koshTraitPct([0, 4, 6, 8, 10], t))
    minus.push('− Спринт заметно быстрее расходует сытость')
  } else if (role === 'fisher') {
    plus.push('+ Удача ' + koshTraitLvl(t))
    plus.push('+ В воде: Грация дельфина')
    if (t >= 3) plus.push('+ В воде: Подводное дыхание')
    minus.push('− Урон в ближнем бою −5%')
  } else if (role === 'lumberjack') {
    plus.push('+ Спешка ' + koshTraitLvl(t) + ' (быстрее работа)')
    plus.push('+ Урон топорами +' + koshTraitPct([0, 4, 6, 8, 10], t))
    minus.push('− Спринт быстрее расходует сытость')
  } else if (role === 'diver') {
    plus.push('+ В воде: Подводное дыхание, Грация дельфина ' + koshTraitLvl(t))
    if (t >= 2) plus.push('+ В воде: Ночное зрение')
    minus.push('− На суше: Замедление I')
    minus.push('− На суше спринт быстрее расходует сытость')
  } else if (role === 'fighter') {
    plus.push('+ Входящий урон −' + koshTraitPct([0, 4, 7, 10, 14], t))
    plus.push('+ Урон в ближнем бою +' + koshTraitPct([0, 3, 5, 7, 10], t))
    minus.push('− Усталость I (медленнее добыча)')
  } else if (role === 'archer') {
    plus.push('+ Скорость ' + koshTraitLvl(t))
    if (t >= 3) plus.push('+ Прыгучесть I')
    plus.push('+ Урон снарядами +' + koshTraitPct([0, 5, 8, 11, 15], t))
    minus.push('− Урон в ближнем бою −10%')
  } else if (role === 'shooter') {
    plus.push('+ Урон снарядами +' + koshTraitPct([0, 7, 10, 14, 18], t))
    if (t >= 3) plus.push('+ Скорость I')
    minus.push('− Урон в ближнем бою −12%')
    minus.push('− Спринт чуть быстрее расходует сытость')
  } else if (role === 'artillery') {
    plus.push('+ Урон от взрывов −' + koshTraitPct([0, 20, 30, 40, 50], t))
    plus.push('+ Прочий входящий урон −' + koshTraitPct([0, 2, 3, 5, 8], t))
    plus.push('+ Урон взрывами +' + koshTraitPct([0, 4, 7, 10, 15], t))
    if (t >= 3) plus.push('+ Огнестойкость')
    minus.push('− Замедление I')
  } else if (role === 'hunter') {
    plus.push('+ Скорость ' + koshTraitLvl(t))
    if (t >= 2) plus.push('+ Ночное зрение')
    plus.push('+ Урон снарядами +' + koshTraitPct([0, 4, 7, 10, 12], t))
    minus.push('− Входящий урон +4%')
  } else if (role === 'researcher') {
    plus.push('+ Удача ' + koshTraitLvl(t))
    if (t >= 2) plus.push('+ Ночное зрение')
    plus.push('+ Урон от среды (огонь, падение, утопление, холод, магия, иссушение) −' + koshTraitPct([0, 8, 12, 16, 20], t))
    minus.push('− Урон в ближнем бою −15%')
  } else if (role === 'pilot') {
    plus.push('+ Плавное падение')
    plus.push('+ Скорость ' + koshTraitLvl(t))
    plus.push('+ Урон от падения −' + koshTraitPct([0, 70, 85, 95, 100], t))
    minus.push('− Прочий входящий урон +5%')
    minus.push('− Усталость I (медленнее добыча)')
  }

  return { plus: plus, minus: minus }
}

// Parses "<namespace>:<role>_<piece>_<i..iv>_test" -> { role, tier } or null.
function koshTraitPiece(stack) {
  if (!stack) return null
  var id = ''
  try {
    if (stack.isEmpty()) return null
    id = String(KoshTraitRegistries.ITEM.getKey(stack.getItem()))
  } catch (e) {
    return null
  }
  var split = id.split(':')
  if (split.length !== 2) return null
  var role = null
  Object.keys(KOSHPACK_TRAIT_IDS).forEach(function (r) {
    if (KOSHPACK_TRAIT_IDS[r] === split[0]) role = r
  })
  if (!role) return null
  var match = split[1].match(new RegExp('^' + role + '_(helmet|chestplate|leggings|boots)_(i|ii|iii|iv)_test$'))
  if (!match) return null
  return { role: role, tier: { i: 1, ii: 2, iii: 3, iv: 4 }[match[2]] }
}

// Counts worn pieces of the given role; returns { worn, minTier } or null without a player.
function koshTraitWorn(role) {
  var player = null
  try { player = KoshTraitMinecraft.getInstance().player } catch (e) {}
  if (!player) return null
  var slots = [KoshTraitSlot.HEAD, KoshTraitSlot.CHEST, KoshTraitSlot.LEGS, KoshTraitSlot.FEET]
  var worn = 0
  var minTier = 4
  slots.forEach(function (slot) {
    var info = null
    try { info = koshTraitPiece(player.getItemBySlot(slot)) } catch (e) {}
    if (info && info.role === role) {
      worn++
      minTier = Math.min(minTier, info.tier)
    }
  })
  return { worn: worn, minTier: minTier }
}

ItemEvents.modifyTooltips(event => {
  Object.keys(KOSHPACK_TRAIT_IDS).forEach(role => {
    event.modify(new RegExp('^' + KOSHPACK_TRAIT_IDS[role] + ':'), builder => {
      builder.dynamic('koshpack_trait_' + role)
    })
  })
})

Object.keys(KOSHPACK_TRAIT_IDS).forEach(role => {
  ItemEvents.dynamicTooltips('koshpack_trait_' + role, event => {
    try {
      var piece = koshTraitPiece(event.item)
      if (!piece) return

      var state = koshTraitWorn(role)
      var tier = piece.tier
      var block = []

      if (state && state.worn === 4) {
        tier = state.minTier
        block.push(Text.of('Черта профессии: активна (уровень ' + KOSH_TRAIT_ROMAN[tier] + ')').aqua())
      } else {
        if (state) block.push(Text.of('Черта не активна: надето ' + state.worn + ' из 4').darkGray())
        block.push(Text.of('При полном комплекте уровня ' + KOSH_TRAIT_ROMAN[tier] + ':').darkGray())
      }

      var lines = koshTraitLines(role, tier)
      lines.plus.forEach(line => block.push(Text.of(line).green()))
      lines.minus.forEach(line => block.push(Text.of(line).red()))
      block.push(Text.of('Сила черты = самый низкий уровень среди 4 надетых деталей.').gray())

      event.add(block)
    } catch (e) {
      // A tooltip must never break item rendering.
    }
  })
})
