/**
 * Copyright 2013 Tim Down.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
function HashSet(t,n){var e=new Hashtable(t,n);this.add=function(t){e.put(t,!0)},this.addAll=function(t){for(var n=0,r=t.length;r>n;++n)e.put(t[n],!0)},this.values=function(){return e.keys()},this.remove=function(t){return e.remove(t)?t:null},this.contains=function(t){return e.containsKey(t)},this.clear=function(){e.clear()},this.size=function(){return e.size()},this.isEmpty=function(){return e.isEmpty()},this.clone=function(){var r=new HashSet(t,n);return r.addAll(e.keys()),r},this.intersection=function(r){for(var i,u=new HashSet(t,n),o=r.values(),s=o.length;s--;)i=o[s],e.containsKey(i)&&u.add(i);return u},this.union=function(t){for(var n,r=this.clone(),i=t.values(),u=i.length;u--;)n=i[u],e.containsKey(n)||r.add(n);return r},this.isSubsetOf=function(t){for(var n=e.keys(),r=n.length;r--;)if(!t.contains(n[r]))return!1;return!0},this.complement=function(e){for(var r,i=new HashSet(t,n),u=this.values(),o=u.length;o--;)r=u[o],e.contains(r)||i.add(r);return i}}