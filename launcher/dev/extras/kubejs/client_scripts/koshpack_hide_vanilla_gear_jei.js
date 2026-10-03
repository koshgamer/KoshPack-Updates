// Match recipe removal and server acquisition policy, including saved equipment.
var KoshViewerGearPolicy = Java.loadClass('ru.koshpack.forgeui.server.VanillaGearPolicy')
RecipeViewerEvents.removeEntriesCompletely('item', function(event) {
  var blocked = KoshViewerGearPolicy.blockedIds().iterator()
  while (blocked.hasNext()) event.remove(String(blocked.next()))
})
