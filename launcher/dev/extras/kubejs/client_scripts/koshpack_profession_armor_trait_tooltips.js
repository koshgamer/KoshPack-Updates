// KoshPack professional armor trait tooltips v1.
// Shows the REAL full-set bonus/drawback implemented by server script.

var KOSHPACK_TRAIT_TOOLTIP = {
  miner: {
    plus: ['+ Быстрее добыча; III+: ночное зрение', '+ IV: Ускорение II'],
    minus: ['− Спринт быстрее расходует сытость']
  },
  engineer: {
    plus: ['+ Быстрее работа; защита от огня растёт с тиром'],
    minus: ['− Урон в ближнем бою ниже']
  },
  scout: {
    plus: ['+ Скорость; III+: высокий прыжок', '+ Сильно меньше урон от падения'],
    minus: ['− Получает на 6% больше обычного урона']
  },
  builder: {
    plus: ['+ Быстрее работа; II+: высокий прыжок', '+ Меньше урон от падения'],
    minus: ['− Спринт быстрее расходует сытость']
  },
  medic: {
    plus: ['+ Периодическая регенерация; сильнее на высоких тирах'],
    minus: ['− На 10% меньше наносимого урона']
  },
  farmer: {
    plus: ['+ Удача; комплект постепенно восстанавливает сытость'],
    minus: ['− На 6% меньше наносимого урона']
  },
  blacksmith: {
    plus: ['+ Сильная защита от огня', '+ Больше урона в ближнем бою'],
    minus: ['− Спринт заметно быстрее расходует сытость']
  },
  fisher: {
    plus: ['+ Удача; быстрее плавает', '+ III+: дыхание под водой'],
    minus: ['− На 5% меньше урона в ближнем бою']
  },
  lumberjack: {
    plus: ['+ Быстрее работа', '+ Больше урона топорами'],
    minus: ['− Спринт быстрее расходует сытость']
  },
  diver: {
    plus: ['+ Под водой: дыхание, скорость; II+: ночное зрение'],
    minus: ['− На суше: Замедление I и повышенный расход сытости']
  },
  fighter: {
    plus: ['+ Меньше входящего урона', '+ Больше урона в ближнем бою'],
    minus: ['− Утомление I при добыче/работе']
  },
  archer: {
    plus: ['+ Скорость; III+: высокий прыжок', '+ Больше урона снарядами'],
    minus: ['− На 10% меньше урона в ближнем бою']
  },
  shooter: {
    plus: ['+ Больше урона снарядами; III+: Скорость I'],
    minus: ['− На 12% меньше урона в ближнем бою', '− Спринт чуть быстрее расходует сытость']
  },
  artillery: {
    plus: ['+ Сильная защита от взрывов', '+ Бонус к урону взрывами; III+: огнестойкость'],
    minus: ['− Замедление I']
  },
  hunter: {
    plus: ['+ Скорость; II+: ночное зрение', '+ Больше урона снарядами'],
    minus: ['− Получает на 4% больше обычного урона']
  },
  researcher: {
    plus: ['+ Удача; II+: ночное зрение', '+ Меньше урон от среды: огонь, падение, яд/магия и т.п.'],
    minus: ['− На 15% меньше урона в ближнем бою']
  },
  pilot: {
    plus: ['+ Медленное падение и скорость', '+ Падение почти безопасно; IV: урон от падения 0'],
    minus: ['− Получает на 5% больше обычного урона', '− Утомление I при добыче/работе']
  }
}

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

ItemEvents.modifyTooltips(event => {
  Object.keys(KOSHPACK_TRAIT_IDS).forEach(role => {
    var ns = KOSHPACK_TRAIT_IDS[role]
    var info = KOSHPACK_TRAIT_TOOLTIP[role]

    event.add(new RegExp('^' + ns + ':'), Text.darkGray('Черта профессии активна при 4 деталях одной профессии.'))
    info.plus.forEach(line => event.add(new RegExp('^' + ns + ':'), Text.green(line)))
    info.minus.forEach(line => event.add(new RegExp('^' + ns + ':'), Text.red(line)))
    event.add(new RegExp('^' + ns + ':'), Text.gray('Сила черты = самый низкий тир среди 4 надетых деталей.'))
  })
})
