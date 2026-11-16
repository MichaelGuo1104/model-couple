export const DESK_WIDTH=1920, DESK_HEIGHT=1080, PAPER_WIDTH=210, PAPER_HEIGHT=297;
export function deskBounds(){const margin=15;return {minX:margin,minY:margin,maxX:DESK_WIDTH-PAPER_WIDTH-margin,maxY:DESK_HEIGHT-PAPER_HEIGHT-margin,divider:DESK_WIDTH*2/3,cardWidth:PAPER_WIDTH};}
export function clampToDesk(x,y,bounds=deskBounds()){return {x:Math.max(bounds.minX,Math.min(bounds.maxX,x)),y:Math.max(bounds.minY,Math.min(bounds.maxY,y))};}
export function zoomAt(camera,point,nextZoom){const zoom=Math.max(.5,Math.min(6,nextZoom)),ratio=zoom/camera.zoom;return {zoom,x:point.x-(point.x-camera.x)*ratio,y:point.y-(point.y-camera.y)*ratio};}
