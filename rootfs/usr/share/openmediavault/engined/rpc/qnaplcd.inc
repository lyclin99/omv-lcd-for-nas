<?php

/**
 * OMV LCD for NAS - OpenMediaVault plugin for the QNAP front LCD
 * Copyright (C) 2026 lyclin99
 * Based on mpeirone/QnapLcdInfo (GPL-3.0).
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
        $this->registerMethod("setTestAlert");
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
            "LCD_CUSTOM_TEXT" => (string)$o->get("customtext"),
            "LCD_SHOW_DISKALERT" => $o->get("showdiskalert") ? "1" : "0"
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

    public function setTestAlert($params, $context)
    {
        $this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
        $file = "/run/lcdinfo_test_alert";
        $enable = is_array($params) && !empty($params["enable"]);
        if ($enable) {
            $msg = (is_array($params) && !empty($params["message"]) && is_string($params["message"]))
                ? $params["message"]
                : "! DISK ALERT !\nsdb BAD SEC:8\n";
            file_put_contents($file, $msg);
        } else {
            @unlink($file);
        }
        return ["test_alert" => file_exists($file)];
    }
}
