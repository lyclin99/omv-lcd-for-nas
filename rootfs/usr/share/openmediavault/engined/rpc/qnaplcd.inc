<?php

namespace Engined\Rpc;

class OMVRpcServiceQnapLcd extends \OMV\Rpc\ServiceAbstract
{
    public function getName()
    {
        return "QnapLcd";
    }

    public function initialize()
    {
        $this->registerMethod("get");
        $this->registerMethod("set");
        $this->registerMethod("getPreview");
    }

    public function get($params, $context)
    {
        $this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
        return \OMV\Rpc\Rpc::call("Config", "get", [
            "id" => "conf.service.qnaplcd"
        ], $context);
    }

    public function set($params, $context)
    {
        $this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
        return \OMV\Rpc\Rpc::call("Config", "set", [
            "id" => "conf.service.qnaplcd",
            "data" => $params
        ], $context);
    }

    public function getPreview($params, $context)
    {
        $this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
        $db = \OMV\Config\Database::getInstance();
        $o = $db->get("conf.service.qnaplcd");
        $env = [
            "LCD_BLANK_TIMEOUT" => (string)$o->get("blanktimeout"),
            "LCD_NETWORK_REGEX" => (string)$o->get("networkregex"),
            "LCD_CUSTOM_TEXT" => (string)$o->get("customtext")
        ];
        foreach (["host", "boot", "memory", "disks", "network", "clock", "custom"] as $k) {
            $env["LCD_SHOW_" . strtoupper($k)] = $o->get("show" . $k) ? "1" : "0";
            $env["LCD_ORDER_" . strtoupper($k)] = (string)$o->get("order" . $k);
        }
        $cmd = "env";
        foreach ($env as $k => $v) {
            $cmd .= " " . escapeshellarg($k . "=" . $v);
        }
        $cmd .= " /opt/QnapLcdInfo/venv/bin/python /opt/QnapLcdInfo/lcdInfo.py --dump-json 2>&1";
        exec($cmd, $output, $rc);
        $data = json_decode(implode("\n", $output), true);
        if ($rc !== 0 || !is_array($data)) {
            throw new \OMV\Exception("Failed to generate the LCD preview.");
        }
        return $data;
    }
}
