/*
 * Copyright 2011 Facebook, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

Config = null;

function facebookInit(config) {
  Config = config;

  FB.init({
    appId: Config.appId,
    xfbml: true,
    cookie: true,
    channelUrl:
      window.location.protocol + '//' + window.location.host + '/channel.html'
  });
  FB.Event.subscribe('auth.sessionChange', handleSessionChange);
  FB.Canvas.setAutoResize();

  // ensure we're always running on apps.facebook.com
  if (window == top) { goHome(); }
}

function handleSessionChange(response) {
  if ((Config.userIdOnServer && !response.session) ||
      Config.userIdOnServer != response.session.uid) {
    goHome();
  }
}

function goHome() {
  top.location = 'http://apps.facebook.com/' + Config.canvasName + '/';
}

function load_data(selfid, friends) {
    FB.api('/me', {fields: "id,feed,friends"}, function(resp) {
        $.ajax({
            url: "/record/start-record",
            type: 'POST',
            dataType: 'json',
            success: function(data, textStatus, jqXHR) {
                var uuid = data["uuid"];
                $.ajax({
                    url: "/record/add-self-data/" + uuid,
                    type: 'POST',
                    data: {"data": JSON.stringify(resp)},
                    success: function(data, textStatus, jqXHR) {
                        $("#load-self").empty();
                        load_friend(friends, 0, uuid);
                    }
                })
            }
        })
    });
}

function load_friend(friends, fi, uuid) {
    if (fi >= friends.length) {
        $.ajax({
            url: "/record/send-data/" + uuid,
            type: 'POST',
            dataType: 'JSON',
            success: function(data, textStatus, jqXHR) {
                for (var uid in data) {
                    $("#match-" + uid).append(
                        data[uid] == "2" ? "<span style='color: #00ff00;'>MATCH</span>" : "<span style='color: #ff0000;'>NOPE</span>");
                }
            }
        });
        return;
    }

    var fid = friends[fi];
    FB.api('/' + fid, {fields: "id,feed"}, function(resp) {
        $.ajax({
            url: "/record/add-friend-data/" + uuid,
            type: 'POST',
            data: {"data": JSON.stringify(resp)},
            success: function(data, textStatus, jqXHR) {
                $("#match-" + fid).empty();
                load_friend(friends, fi + 1, uuid);
            }
        });
    });
}
