<?php

namespace Engined\Module;

class QnapLcd extends \OMV\Engine\Module\ServiceAbstract implements \OMV\Engine\Notify\IListener, \OMV\Engine\Module\IServiceStatus
{
    public function getName()
    {
        return "qnaplcd";
    }

    public function getStatus()
    {
        $db = \OMV\Config\Database::getInstance();
        $object = $db->get("conf.service.qnaplcd");
        $systemCtl = new \OMV\System\SystemCtl("lcdinfo");
        return [
            "name" => $this->getName(),
            "title" => gettext("OMV LCD for NAS"),
            "enabled" => $object->get("enable"),
            "running" => $systemCtl->isActive()
        ];
    }

    public function bindListeners(\OMV\Engine\Notify\Dispatcher $dispatcher)
    {
        $dispatcher->addListener(
            OMV_NOTIFY_MODIFY,
            "org.openmediavault.conf.service.qnaplcd",
            [$this, "setDirty"]
        );
    }
}
