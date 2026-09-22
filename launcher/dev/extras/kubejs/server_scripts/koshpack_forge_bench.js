// KoshPack unified sharpening / modification bench v0.1.
//
// This is the first executable vertical slice for the FINAL shared system:
// - one physical forge bench;
// - persistent 2-3 modification slots stored in minecraft:custom_data;
// - sequential I -> II -> III -> IV upgrades;
// - free removal without material refund;
// - armor, weapons and tools share the same data model.
//
// Runtime slice enabled in v0.1:
// armor  -> Reinforcement I-IV
// weapon -> Fine Honing I-IV
// tool   -> Aggressive Geometry I-IV
//
// More approved catalog entries are added on this base after live acceptance.

var KOSH_FORGE_SESSIONS = {}

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
  reinforcement: {
    name: 'Укреплённая броня',
    category: 'armor',
    icon: 'minecraft:iron_chestplate',
    max: 4,
    description: 'Снижает подходящий входящий урон.',
    base: [
      { ingredient: 'minecraft:iron_ingot', count: 4, label: 'Железный слиток' },
      { ingredient: 'minecraft:leather', count: 2, label: 'Кожа' }
    ]
  },
  fine_honing: {
    name: 'Тонкая заточка',
    category: 'weapon',
    icon: 'minecraft:iron_sword',
    max: 4,
    description: 'Увеличивает урон ближнего боя ценой более узкой специализации.',
    base: [
      { ingredient: 'minecraft:quartz', count: 2, label: 'Кварц' },
      { ingredient: 'minecraft:iron_ingot', count: 1, label: 'Железный слиток' }
    ]
  },
  aggressive_geometry: {
    name: 'Агрессивная геометрия',
    category: 'tool',
    icon: 'minecraft:iron_pickaxe',
    max: 4,
    description: 'Ускоряет работу подходящим инструментом.',
    base: [
      { ingredient: 'minecraft:quartz', count: 2, label: 'Кварц' },
      { ingredient: 'minecraft:flint', count: 2, label: 'Кремень' }
    ]
  }
}

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

function koshForgeClassify(stack) {
  var id = koshForgeStackId(stack)
  if (!id || id === 'minecraft:air') return null

  var split = id.split(':')
  if (split.length === 2 && KOSH_ARMOR_NAMESPACES[split[0]]) {
    return { category: 'armor', slots: 3, tier: koshForgeArmorTier(split[1]) }
  }

  if (
    koshForgeHasTag(stack, 'minecraft:swords') ||
    koshForgeHasTag(stack, 'minecraft:axes') ||
    koshForgeHasTag(stack, 'minecraft:tridents') ||
    koshForgeHasTag(stack, 'minecraft:bows') ||
    koshForgeHasTag(stack, 'minecraft:crossbows') ||
    split[0] === 'simplyswords'
  ) {
    var light = /dagger|sai|chakram|rapier/.test(split[1])
    return { category: 'weapon', slots: light ? 2 : 3, tier: 4 }
  }

  if (
    koshForgeHasTag(stack, 'minecraft:pickaxes') ||
    koshForgeHasTag(stack, 'minecraft:shovels') ||
    koshForgeHasTag(stack, 'minecraft:hoes')
  ) {
    return { category: 'tool', slots: 3, tier: 4 }
  }

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

function koshForgeLevelCost(mod, nextLevel) {
  var out = []
  for (var i = 0; i < mod.base.length; i++) out.push(mod.base[i])

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

function koshForgeReturnTarget(player, session) {
  var target = session.target
  if (!target) return

  var slot = session.selectedSlot
  var current = player.inventory.getStackInSlot(slot)
  try {
    if (current.empty) {
      player.inventory.setStackInSlot(slot, target)
      session.target = null
      return
    }
  } catch (e) {}

  player.give(target)
  session.target = null
}

function koshForgeFinalize(player, key) {
  var session = KOSH_FORGE_SESSIONS[key]
  if (!session || session.finished) return
  session.finished = true

  var pending = session.pending
  if (!pending) {
    koshForgeReturnTarget(player, session)
    delete KOSH_FORGE_SESSIONS[key]
    return
  }

  if (pending.kind === 'remove') {
    koshForgeWriteSlot(session.target, pending.slot, '', 0)
    player.tell(Text.yellow('Заточка снята. Материалы не возвращены.'))
    koshForgeReturnTarget(player, session)
    delete KOSH_FORGE_SESSIONS[key]
    return
  }

  var mod = KOSH_FORGE_MODS[pending.modId]
  var info = koshForgeClassify(session.target)
  if (!mod || !info || mod.category !== info.category) {
    player.tell(Text.red('Эта модификация несовместима с предметом.'))
    koshForgeReturnTarget(player, session)
    delete KOSH_FORGE_SESSIONS[key]
    return
  }

  var current = koshForgeReadSlot(session.target, pending.slot)
  var nextLevel = current && current.id === pending.modId ? current.level + 1 : 1

  if (nextLevel > mod.max) {
    player.tell(Text.yellow('У этой заточки уже максимальный уровень.'))
    koshForgeReturnTarget(player, session)
    delete KOSH_FORGE_SESSIONS[key]
    return
  }

  if (info.category === 'armor' && nextLevel > info.tier) {
    player.tell(Text.red('Уровень заточки не может быть выше уровня этой брони.'))
    koshForgeReturnTarget(player, session)
    delete KOSH_FORGE_SESSIONS[key]
    return
  }

  for (var i = 0; i < info.slots; i++) {
    if (i === pending.slot) continue
    var other = koshForgeReadSlot(session.target, i)
    if (other && other.id === pending.modId) {
      player.tell(Text.red('Одинаковая заточка не может занимать два слота.'))
      koshForgeReturnTarget(player, session)
      delete KOSH_FORGE_SESSIONS[key]
      return
    }
  }

  var cost = koshForgeLevelCost(mod, nextLevel)
  if (!koshForgePay(player, cost)) {
    player.tell(Text.red('Не хватает материалов: ' + koshForgeCostText(cost)))
    koshForgeReturnTarget(player, session)
    delete KOSH_FORGE_SESSIONS[key]
    return
  }

  koshForgeWriteSlot(session.target, pending.slot, pending.modId, nextLevel)
  player.tell(Text.green(mod.name + ' ' + ['','I','II','III','IV'][nextLevel] + ' установлена.'))

  koshForgeReturnTarget(player, session)
  delete KOSH_FORGE_SESSIONS[key]
}

function koshForgeQueueFinalize(player, key) {
  var session = KOSH_FORGE_SESSIONS[key]
  if (!session || session.returnScheduled) return
  session.returnScheduled = true

  player.server.scheduleInTicks(1, function() {
    koshForgeFinalize(player, key)
  })
}

function koshForgeOpenModifierPage(player, key, slotIndex) {
  var session = KOSH_FORGE_SESSIONS[key]
  if (!session) return
  var info = koshForgeClassify(session.target)
  if (!info) return

  player.openChestGUI(Text.of('Кузнечный стенд'), 6, function(gui) {
    gui.playerSlots = false

    gui.button(4, 0, session.target.copy(), Text.gold('Обрабатываемый предмет'), function(e) {
      e.setHandled()
    })

    var current = koshForgeReadSlot(session.target, slotIndex)
    if (current) {
      var cm = KOSH_FORGE_MODS[current.id]
      var removeIcon = Item.of('minecraft:barrier')
      gui.button(8, 5, removeIcon, Text.red('Снять: ' + (cm ? cm.name : current.id)), function(e) {
        session.pending = { kind: 'remove', slot: slotIndex }
        player.closeMenu()
      })
    }

    var x = 1
    Object.keys(KOSH_FORGE_MODS).forEach(function(modId) {
      var mod = KOSH_FORGE_MODS[modId]
      if (mod.category !== info.category) return

      var installed = current && current.id === modId ? current.level : 0
      var next = installed + 1
      var label = mod.name + ' ' + (next <= mod.max ? ['','I','II','III','IV'][next] : 'MAX')
      var icon = Item.of(mod.icon)
      gui.button(x, 2, icon, Text.aqua(label), function(e) {
        if (next > mod.max) {
          player.tell(Text.yellow('Уже максимальный уровень.'))
          return
        }

        var cost = koshForgeLevelCost(mod, next)
        player.tell(Text.gray(mod.description))
        player.tell(Text.gray('Цена: ' + koshForgeCostText(cost)))
        session.pending = { kind: 'apply', slot: slotIndex, modId: modId }
        player.closeMenu()
      })
      x += 2
    })

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
  var info = koshForgeClassify(session.target)
  if (!info) return

  player.openChestGUI(Text.of('Кузнечный стенд'), 6, function(gui) {
    gui.playerSlots = false

    gui.button(4, 0, session.target.copy(), Text.gold('Обрабатываемый предмет'), function(e) {
      e.setHandled()
    })

    for (var i = 0; i < info.slots; i++) {
      ;(function(slotIndex) {
        var current = koshForgeReadSlot(session.target, slotIndex)
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

  var target = held.copy()
  target.count = 1
  var selected = player.selectedSlot

  if (held.count > 1) {
    held.count = held.count - 1
  } else {
    player.mainHandItem = Item.empty
  }

  KOSH_FORGE_SESSIONS[key] = {
    target: target,
    selectedSlot: selected,
    pending: null,
    returnScheduled: false,
    finished: false
  }

  koshForgeOpenMain(player, key)
  event.cancel()
})
