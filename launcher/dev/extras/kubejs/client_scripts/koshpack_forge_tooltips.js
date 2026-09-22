// KoshPack Forge dynamic modifier tooltip v0.1.

function koshClientForgeRead(item, slot) {
  try {
    var tag = item.getCustomData()
    var id = String(tag.getString('kosh_forge_slot_' + slot + '_id').orElse(''))
    var level = Number(tag.getInt('kosh_forge_slot_' + slot + '_level').orElse(0))
    if (id && level > 0) return { id: id, level: level }
  } catch (e) {}
  return null
}

var KOSH_CLIENT_FORGE_NAMES = {
  reinforcement: 'Укреплённая броня',
  fine_honing: 'Тонкая заточка',
  aggressive_geometry: 'Агрессивная геометрия'
}

ItemEvents.modifyTooltips(event => {
  event.modifyAll(builder => {
    builder.dynamic('koshpack_forge_slots')
  })
})

ItemEvents.dynamicTooltips('koshpack_forge_slots', event => {
  var found = []
  for (var i = 0; i < 3; i++) {
    var s = koshClientForgeRead(event.item, i)
    if (s) found.push('◇ ' + (KOSH_CLIENT_FORGE_NAMES[s.id] || s.id) + ' ' + ['','I','II','III','IV'][s.level])
  }

  if (found.length <= 0) return

  event.add([Text.darkGray('Кузнечные модификации:')])
  for (var j = 0; j < found.length; j++) event.add([Text.aqua(found[j])])
})
